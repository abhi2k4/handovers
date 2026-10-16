"""End-to-end over a freshly seeded graph: the planted storylines must be found exactly.

Runs against whatever FalkorDB is configured (CI: falkordb/falkordb:6.0.1). No LLM: every output
uses its deterministic fallback, so assertions are stable.
"""

import json
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from core.clock import OPEN, now_ms
from core.config import Settings, get_settings
from core.falkordb import FalkorDBClient
from core.graph import Graph, QueryCatalog
from core.llm import LLM
from seed.load import bootstrap, load
from services import access, analysis, companion, generators, kpis, ramp
from services import handover as svc

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def graph() -> AsyncIterator[Graph]:
    settings = Settings(handovers_tenant="itest_flow")
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


@pytest.fixture(scope="module")
def llm() -> LLM:
    return LLM(Settings(llm_provider="none"))


def answers() -> dict[str, str]:
    path = get_settings().graph_dir / "seed" / "northwind" / "interview.json"
    data: dict[str, str] = json.loads(path.read_text(encoding="utf-8"))
    return data


@pytest.mark.asyncio(loop_scope="module")
async def test_gap_rules_find_the_planted_storylines(graph: Graph) -> None:
    arjun = {(s.rule, s.target) for s in await analysis.find_gaps(graph, "emp:arjun")}
    assert ("G1", "clm:recon-retry-limit@2025") in arjun
    assert ("G6", "clm:recon-retry-limit@runbook") in arjun
    assert ("G8", "resp:ledger-unstick") in arjun
    assert ("G7A", "acc:acmebank-portal") in arjun
    assert ("G7S", "sth:acmebank-leena") in arjun
    # Control: Settlement v2 is shared with Rohan, so nothing about it is at risk.
    assert not any("settle" in t for _, t in arjun)
    # Personal notes never become questions.
    assert not any("career" in t for _, t in arjun)

    nisha = {(s.rule, s.target) for s in await analysis.find_gaps(graph, "emp:nisha")}
    assert ("G1", "dec:pause-google-ads") in nisha
    assert ("G6", "clm:cac-target@q2") in nisha
    assert ("G8", "resp:utm-rebuild") in nisha
    assert ("G7A", "acc:meta-business-manager") in nisha
    assert not any("reels" in t for _, t in nisha)


@pytest.mark.asyncio(loop_scope="module")
async def test_jd_is_built_from_real_work_and_diffs_the_old_one(graph: Graph, llm: LLM) -> None:
    jd = await generators.build_jd(graph, llm, "emp:arjun")
    titles = [r["text"] for r in jd["responsibilities"]]
    assert titles[0].startswith("Own the reconciliation service")
    assert "Python" in [s["name"] for s in jd["must"]]
    assert any("Java" in line for line in jd["diff"]["unused"])
    assert any(m["id"] == "resp:ledger-unstick" for m in jd["diff"]["missing"])
    assert not any("communication" in line.lower() for line in jd["diff"]["unused"])


@pytest.mark.asyncio(loop_scope="module")
async def test_successor_abstains_before_and_answers_after_transfer(graph: Graph, llm: LLM) -> None:
    before = await companion.ask(
        graph, llm, "emp:farhan", "Why does the reconciliation service retry only 3 times?"
    )
    assert before["status"] == "abstained" and before["citations"] == []
    assert any(a["name"] == "Arjun Mehta" for a in before["ask"])

    hid = await svc.open_handover(graph, "emp:arjun", "emp:farhan", 30)
    h = await svc.get(graph, hid)
    script = answers()
    for gap in svc.interview_questions(h["gaps"]):
        if gap["target_id"] in script:
            preview = await svc.preview_answer(graph, llm, gap["id"], script[gap["target_id"]])
            await svc.confirm_answer(graph, gap["id"], script[gap["target_id"]], preview["facts"])
    preview = await svc.transfer_preview(graph, hid)
    assert [e["reason"] for e in preview["exclude"]] == ["personal"]
    result = await svc.approve_and_transfer(graph, hid, "emp:priya")
    assert result["knowledge"] >= 8 and result["responsibilities"] == 7

    after = await companion.ask(
        graph, llm, "emp:farhan", "Why does the reconciliation service retry only 3 times?"
    )
    assert after["status"] == "answered"
    top = after["citations"][0]
    assert top["id"] == "clm:recon-retry-limit@2025"
    assert top["from"] == "Arjun Mehta" and top["approved_by"] == "Priya Nair"
    assert "idempotency" in after["answer"]

    how = await companion.ask(graph, llm, "emp:farhan", "How do I unstick a ledger export batch?")
    assert how["status"] == "answered" and "export_locks" in how["answer"]

    trap = await companion.ask(
        graph, llm, "emp:farhan", "What did Arjun say about career plans in his 1:1?"
    )
    assert trap["status"] == "abstained"


@pytest.mark.asyncio(loop_scope="module")
async def test_nothing_new_means_no_followup_transfer(graph: Graph) -> None:
    hid = next(
        h["id"] for h in await graph.read("handover_list", {}) if h["employee_id"] == "emp:arjun"
    )
    h = await svc.get(graph, hid)
    assert h["status"] == "transferred" and await svc.pending_followup(graph, h) == 0
    with pytest.raises(svc.Conflict):
        await svc.approve_and_transfer(graph, hid, "emp:priya")


@pytest.mark.asyncio(loop_scope="module")
async def test_every_read_model_and_the_marketing_flow(graph: Graph, llm: LLM) -> None:
    """Touches every read path, including decisions with null fields (a FalkorDB 6.0.1 crash case)."""
    people = await analysis.people(graph)
    assert len(people) == 17
    for p in people:
        assert await analysis.person(graph, p["id"]) is not None

    hid = await svc.open_handover(graph, "emp:nisha", "emp:ananya", 30)
    for kind in svc.ARTIFACT_KINDS:
        assert await svc.artifact(graph, llm, hid, kind)
    h = await svc.get(graph, hid)
    script = answers()
    asked = svc.interview_questions(h["gaps"])
    assert asked[0]["rule"] == "G1"
    late = "resp:utm-rebuild"  # answered only after the approval, below
    for gap in asked:
        if gap["target_id"] in script and gap["target_id"] != late:
            preview = await svc.preview_answer(graph, llm, gap["id"], script[gap["target_id"]])
            await svc.confirm_answer(graph, gap["id"], script[gap["target_id"]], preview["facts"])
    before = await analysis.person(graph, "emp:nisha")
    assert before is not None
    expected = len(ramp.build_items(access.hide_private(before), "Aditi Menon"))
    await svc.approve_and_transfer(graph, hid, "emp:aditi")
    # A plan made after the approval still covers the work Nisha held, though it has moved.
    plan = await ramp.generate(graph, hid)
    assert plan["total"] == expected and any(i["kind"] == "take-over" for i in plan["items"])
    assert await graph.read("handover_list", {})
    assert await graph.one("transfer_for_handover", {"handover": hid})

    cac = await companion.ask(graph, llm, "emp:ananya", "What is the blended CAC target?")
    assert cac["status"] == "answered" and cac["citations"][0]["id"] == "clm:cac-target@jul"
    salary = await companion.ask(graph, llm, "emp:ananya", "What salary is Nisha asking for?")
    assert salary["status"] == "abstained"
    unknown = await companion.ask(
        graph, llm, "emp:ananya", "How do I deploy the reconciliation service?"
    )
    assert unknown["status"] == "abstained" and unknown["ask"]

    # Nisha answers one more question after the approval: it reaches Ananya via a follow-up.
    gap = next(g for g in asked if g["target_id"] == late)
    preview = await svc.preview_answer(graph, llm, gap["id"], script[late])
    await svc.confirm_answer(graph, gap["id"], script[late], preview["facts"])
    assert await svc.pending_followup(graph, await svc.get(graph, hid)) > 0
    result = await svc.approve_and_transfer(graph, hid, "emp:aditi")
    assert result["followup"] and result["knowledge"] > 0 and result["responsibilities"] == 0
    assert await svc.pending_followup(graph, await svc.get(graph, hid)) == 0
    how = await companion.ask(graph, llm, "emp:ananya", "How do I do the month-end UTM rebuild?")
    assert how["status"] == "answered"


@pytest.mark.asyncio(loop_scope="module")
async def test_outcome_kpis_are_measured_from_completed_handovers(graph: Graph) -> None:
    """Arjun's and Nisha's handovers completed above, both before their last day."""
    rows = await graph.read("kpi_handover_outcomes", {})
    assert len(rows) == 2 and all(r["handed_at"] <= r["effective_at"] for r in rows)
    out = {o["key"]: o for o in (await kpis.build(graph))["outcomes"]}
    assert out["on_time"]["value"] == 100
    assert out["knowledge_passed"]["value"] == sum(r["knowledge"] for r in rows) >= 8
    assert out["exit_answers"]["value"] is not None


@pytest.mark.asyncio(loop_scope="module")
async def test_reassigning_an_account_and_adding_a_backup_close_the_risk(graph: Graph) -> None:
    now = now_ms()
    await graph.run(
        "account_reassign",
        {
            "account": "acc:acmebank-portal",
            "to": "emp:rohan",
            "handover": "",
            "now": now,
            "open": OPEN,
            "leaver_until": OPEN,
        },
    )
    arjun = {(s.rule, s.target) for s in await analysis.find_gaps(graph, "emp:arjun")}
    assert ("G7A", "acc:acmebank-portal") not in arjun

    params = {"id": "resp:ledger-unstick", "now": now}
    before = {r["id"] for r in await graph.read("resp_owners", params)}
    assert before and "emp:rohan" not in before
    await graph.run(
        "resp_assign_backup",
        {"id": "resp:ledger-unstick", "emp": "emp:rohan", "now": now, "open": OPEN, "by": "test"},
    )
    owners = {r["id"] for r in await graph.read("resp_owners", params)}
    assert owners == before | {"emp:rohan"}
