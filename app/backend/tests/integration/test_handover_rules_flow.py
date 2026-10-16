"""The handover loopholes, closed, over a freshly seeded graph (docs/handover-rules.md)."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from core.clock import now_ms
from core.config import Settings
from core.falkordb import FalkorDBClient
from core.graph import Graph, QueryCatalog
from core.llm import LLM
from seed.load import bootstrap, load
from services import access, handover_rules, jobs, org_policy
from services import handover as svc

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def graph() -> AsyncIterator[Graph]:
    settings = Settings(handovers_tenant="itest_rules")
    client = FalkorDBClient(settings)
    if not (await client.status()).ok:
        await client.close()
        pytest.skip("FalkorDB not reachable")
    if await client.graph_exists():
        await client.graph().delete()
    g = Graph(client, QueryCatalog(settings.graph_dir))
    await bootstrap(g)
    await load(g)
    yield g
    await client.graph().delete()
    await client.close()


@pytest.mark.asyncio(loop_scope="module")
async def test_successor_rules_and_mandatory_questions(graph: Graph) -> None:
    with pytest.raises(svc.Conflict, match="own successor"):
        await svc.open_handover(graph, "emp:nisha", "emp:nisha", 30)
    # Arjun (Engineering) for Nisha (Growth): allowed only once confirmed.
    with pytest.raises(svc.NeedsConfirmation) as other:
        await svc.open_handover(graph, "emp:nisha", "emp:arjun", 30)
    assert other.value.code == "other_team"
    hid = await svc.open_handover(graph, "emp:nisha", "emp:ananya", 30)
    h = await svc.get(graph, hid)
    mandatory = [g for g in h["gaps"] if g["rule"] == handover_rules.MANDATORY]
    assert len(mandatory) == len(org_policy.DEFAULTS["mandatory_questions"])
    assert all(g["interview"] and g["mandatory"] for g in mandatory)
    with pytest.raises(svc.Conflict, match="policy"):
        await svc.dismiss_gap(graph, mandatory[0]["id"], "emp:aditi")
    # Someone leaving can't be chosen: Nisha now has a handover.
    with pytest.raises(svc.Conflict, match="leaving too"):
        await svc.open_handover(graph, "emp:kabir", "emp:nisha", 30)
    # HR adds a follow-up; it becomes a required question.
    gid = await svc.add_question(graph, hid, "Which agency invoices are still unpaid?", "emp:meera")
    h = await svc.get(graph, hid)
    assert next(g for g in h["gaps"] if g["id"] == gid)["interview"]


@pytest.mark.asyncio(loop_scope="module")
async def test_the_leaver_picks_the_current_claim_and_both_claims_stay(graph: Graph) -> None:
    hid = (await graph.read("handover_open_for_employee", {"emp": "emp:nisha"}))[0]["id"]
    h = await svc.get(graph, hid)
    g6 = next(g for g in h["gaps"] if g["rule"] == "G6")
    preview = await svc.preview_answer(graph, LLM(Settings(llm_provider="none")), g6["id"], "x")
    ids = {c["id"] for c in preview["choices"]}
    assert len(ids) == 2
    # The leaver says the *older* claim is still the current one: it must be the one kept.
    keep = g6["target_id"]
    await svc.confirm_answer(
        graph, g6["id"], "The older figure still holds.", preview["facts"], keep
    )
    other = (ids - {keep}).pop()
    rows = await graph.raw(
        "MATCH (k:Knowledge) WHERE k.id IN [$a, $b] RETURN k.id AS id, k.status AS status",
        {"a": keep, "b": other},
    )
    status = {r["id"]: r["status"] for r in rows}
    assert status[other] == "superseded" and status[keep] != "superseded"
    links = await graph.raw(
        "MATCH (d:Knowledge)-[:CONFIRMS]->(:Knowledge {id: $k}) MATCH (d)-[:RESOLVES]->(:Knowledge {id: $o}) "
        "RETURN count(d) AS n",
        {"k": keep, "o": other},
    )
    assert links[0]["n"] == 1
    # The answer is the reason Ask gives for the kept claim, not "sources disagree".
    ctx = await graph.read("companion_context", {"emp": "emp:nisha", "ids": [keep]})
    confirmed = await graph.raw(
        "MATCH (d:Decision)-[:CONFIRMS]->(:Knowledge {id: $k}) RETURN d.id AS id", {"k": keep}
    )
    assert len(ctx) == 1 and ctx[0]["decision_id"] == confirmed[0]["id"]


@pytest.mark.asyncio(loop_scope="module")
async def test_approval_keeps_the_leaver_until_the_last_day_then_the_job_departs_them(
    graph: Graph,
) -> None:
    hid = (await graph.read("handover_open_for_employee", {"emp": "emp:nisha"}))[0]["id"]
    out = await svc.reject_transfer(graph, hid, "emp:aditi", "Add the agency contacts first.")
    assert out["decision"] == "rejected"
    assert (await svc.get(graph, hid))["transfer"]["decision"] == "rejected"
    await svc.approve_and_transfer(graph, hid, "emp:aditi")
    nisha = await graph.one("successor_candidate", {"id": "emp:nisha"})
    assert nisha and nisha["status"] == "active"  # still here, can still sign in
    assert await graph.read("employee_by_email", {"email": "nisha@northwind.example"})
    # A transferred handover can't be withdrawn any more.
    with pytest.raises(svc.Conflict, match="transfer is approved"):
        await svc.cancel(graph, hid, "emp:meera", "Withdrawn")
    # The last day arrives: the depart job marks her as left and ends her access.
    await graph.raw(
        "MATCH (h:Handover {id: $id}) SET h.effective_at = $now", {"id": hid, "now": now_ms()}
    )
    await jobs.enqueue(graph, "depart", now_ms(), f"depart:{hid}", handover=hid)
    await graph.raw(
        "MATCH (j:Job {key: $k}) SET j.run_at = $now", {"k": f"depart:{hid}", "now": now_ms()}
    )
    ran = await jobs.run_due(graph)
    assert any(r["kind"] == "depart" and r["status"] == "done" for r in ran)
    assert (await graph.one("successor_candidate", {"id": "emp:nisha"}) or {})[
        "status"
    ] == "departed"
    live = await graph.raw(
        "MATCH (:Employee {id: 'emp:nisha'})-[ha:HAS_ACCESS]->() WHERE ha.until > $now RETURN count(ha) AS n",
        {"now": now_ms()},
    )
    assert live[0]["n"] == 0


@pytest.mark.asyncio(loop_scope="module")
async def test_cancel_within_the_window_and_approver_fallback(graph: Graph) -> None:
    hid = await svc.open_handover(graph, "emp:kabir", None, 30)
    assert (await svc.get(graph, hid))["status"] != "cancelled"
    await svc.cancel(graph, hid, "emp:meera", "Resignation withdrawn on 12 Oct")
    h = await svc.get(graph, hid)
    assert h["status"] == "cancelled" and h["cancel_reason"].startswith("Resignation")
    queued = [j for j in await graph.read("job_list", {"limit": 100}) if j["handover"] == hid]
    assert queued and all(j["status"] == "cancelled" for j in queued)

    # Aditi (Kabir's and Ananya's manager) resigns: Ananya's approver becomes Kavya, one level up.
    await svc.open_handover(graph, "emp:aditi", None, 30)
    await svc.open_handover(graph, "emp:ananya", None, 30)
    routes = await access.approval_routes(graph)
    assert routes["emp:ananya"]["id"] == "emp:kavya"
    assert routes["emp:ananya"]["via"] == "skip-level manager"
    kavya = await access.load_caller(graph, "emp:kavya")
    assert kavya and access.can_approve(kavya, "emp:ananya")
    aditi = await access.load_caller(graph, "emp:aditi")
    assert aditi and not access.can_approve(aditi, "emp:ananya")


@pytest.mark.asyncio(loop_scope="module")
async def test_policy_round_trip_and_job_retries(graph: Graph) -> None:
    p = await org_policy.load(graph)
    saved = await org_policy.save(graph, p | {"withdrawal_days": 3}, "emp:meera")
    assert saved["version"] == 1 and (await org_policy.load(graph))["withdrawal_days"] == 3
    await jobs.enqueue(graph, "nonsense", now_ms(), "bad:1")
    ran = await jobs.run_due(graph)
    bad = next(r for r in ran if r["key"] == "bad:1")
    assert bad["status"] == "queued" and "unknown job kind" in bad["error"]  # retried later
