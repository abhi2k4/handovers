"""Double clicks, crafted requests and early runs against a freshly seeded graph.

Each test pins a bug found while stress-testing the running app: the graph must end up the same
whether a button is pressed once or ten times at once, and a request may only change what its
sender is allowed to change.
"""

import asyncio
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from core.config import Settings
from core.falkordb import FalkorDBClient
from core.graph import Graph, QueryCatalog
from core.llm import LLM
from seed.load import bootstrap, load
from services import companion, jobs, ramp
from services import handover as svc

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def graph() -> AsyncIterator[Graph]:
    settings = Settings(handovers_tenant="itest_hardening")
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


async def _count(graph: Graph, query: str, params: dict[str, str]) -> int:
    rows = await graph._client.graph().ro_query(query, params)
    return int(rows.result_set[0][0])


@pytest.mark.asyncio(loop_scope="module")
async def test_ten_clicks_on_start_open_one_handover(graph: Graph) -> None:
    results = await asyncio.gather(
        *[svc.open_handover(graph, "emp:arjun", "emp:farhan", 30) for _ in range(10)],
        return_exceptions=True,
    )
    opened = [r for r in results if isinstance(r, str)]
    assert len(opened) == 1
    assert all(isinstance(r, svc.Conflict) for r in results if not isinstance(r, str))
    assert (
        await _count(
            graph,
            "MATCH (h:Handover)-[:FOR]->(:Employee {id: $e}) RETURN count(h)",
            {"e": "emp:arjun"},
        )
        == 1
    )


@pytest.mark.asyncio(loop_scope="module")
async def test_a_confirmed_answer_records_only_what_the_gap_allows(graph: Graph, llm: LLM) -> None:
    hid = (await graph.read("handover_open_for_employee", {"emp": "emp:arjun"}))[0]["id"]
    gap = next(g for g in (await svc.get(graph, hid))["gaps"] if g["rule"] == "G1")
    preview = await svc.preview_answer(graph, llm, gap["id"], "We cap retries at 3 to avoid fees.")
    # A crafted request: someone else's knowledge id, a SUPERSEDES target and extra people.
    crafted = [
        {
            **preview["facts"][0],
            "key": "dec:not-yours",
            "kind": "access",
            "supersedes": "clm:recon-retry-limit@runbook",
            "people": ["emp:kavya"],
            "title": "Retries capped at 3",
        }
    ]
    both = await asyncio.gather(
        svc.confirm_answer(graph, gap["id"], "We cap retries at 3 to avoid fees.", crafted),
        svc.confirm_answer(graph, gap["id"], "We cap retries at 3 to avoid fees.", crafted),
        return_exceptions=True,
    )
    done = [r for r in both if isinstance(r, dict)]
    assert len(done) == 1 and isinstance(next(r for r in both if r not in done), svc.Conflict)
    assert done[0]["facts"] == [f["key"] for f in preview["facts"]]  # the server's key, not ours
    assert "dec:not-yours" not in done[0]["facts"]
    # The leaver's wording is kept.
    title = await _count(
        graph,
        "MATCH (k:Knowledge {id: $id}) WHERE k.title = 'Retries capped at 3' RETURN count(k)",
        {"id": preview["facts"][0]["key"]},
    )
    assert title == 1


@pytest.mark.asyncio(loop_scope="module")
async def test_double_approval_makes_one_transfer_and_ramp_plan(graph: Graph) -> None:
    hid = (await graph.read("handover_open_for_employee", {"emp": "emp:arjun"}))[0]["id"]
    with pytest.raises(svc.Conflict):
        await svc.approve_and_transfer(graph, hid, "emp:nobody")  # not a real approver
    results = await asyncio.gather(
        *[svc.approve_and_transfer(graph, hid, "emp:priya") for _ in range(5)],
        return_exceptions=True,
    )
    assert sum(isinstance(r, dict) for r in results) == 1
    q = "MATCH (:Handover {id: $h})-[:HAS_TRANSFER]->(t:Transfer) RETURN count(t)"
    assert await _count(graph, q, {"h": hid}) == 1
    await asyncio.gather(*[ramp.generate(graph, hid) for _ in range(5)])
    q = "MATCH (p:RampPlan)-[:FROM]->(:Handover {id: $h}) RETURN count(p)"
    assert await _count(graph, q, {"h": hid}) == 1


@pytest.mark.asyncio(loop_scope="module")
async def test_a_companion_session_belongs_to_its_person(graph: Graph, llm: LLM) -> None:
    await companion.ask(graph, llm, "emp:farhan", "Who owns the AcmeBank portal?", "ses:farhan")
    mine = await graph.read(
        "session_turns", {"session": "ses:farhan", "emp": "emp:farhan", "limit": 4}
    )
    theirs = await graph.read(
        "session_turns", {"session": "ses:farhan", "emp": "emp:rohan", "limit": 4}
    )
    assert mine and not theirs
    # Someone else's session id adds nothing to it.
    await companion.ask(graph, llm, "emp:rohan", "What is the retry limit?", "ses:farhan")
    after = await graph.read(
        "session_turns", {"session": "ses:farhan", "emp": "emp:farhan", "limit": 4}
    )
    assert len(after) == len(mine)


@pytest.mark.asyncio(loop_scope="module")
async def test_text_with_a_nul_character_is_stored_not_a_server_error(graph: Graph) -> None:
    assert await graph.read("handover_open_for_employee", {"emp": "emp:\x00arjun"})


@pytest.mark.asyncio(loop_scope="module")
async def test_only_the_leavers_own_accounts_can_be_reassigned(graph: Graph) -> None:
    hid = (await graph.read("handover_open_for_employee", {"emp": "emp:arjun"}))[0]["id"]
    held = {"handover": hid, "account": "acc:acmebank-portal"}
    assert await graph.one("leaver_holds_account", held) is not None
    other = {"handover": hid, "account": "acc:not-arjuns"}
    assert await graph.one("leaver_holds_account", other) is None


@pytest.mark.asyncio(loop_scope="module")
async def test_running_a_departure_early_puts_it_back_for_the_last_day(graph: Graph) -> None:
    hid = await svc.open_handover(graph, "emp:rohan", None, 30)
    job = next(
        j for j in await graph.read("job_list", {"limit": 500}) if j["key"] == f"depart:{hid}"
    )
    await graph.run("job_run_now", {"id": job["id"], "now": 0})
    await jobs.run_due(graph)
    after = next(j for j in await graph.read("job_list", {"limit": 500}) if j["id"] == job["id"])
    assert after["status"] == "queued"
    assert after["run_at"] == (await svc.get(graph, hid))["effective_at"]
    emp = await graph.one("successor_candidate", {"id": "emp:rohan"})
    assert emp is not None and emp["status"] != "departed"
