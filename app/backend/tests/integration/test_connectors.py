"""A connector sync end to end against FalkorDB, with recorded platform responses (no network)."""

from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
import pytest_asyncio
from pydantic import SecretStr

from core.config import Settings
from core.falkordb import FalkorDBClient
from core.graph import Graph, QueryCatalog
from core.llm import LLM
from seed.load import bootstrap, load
from services import sync

pytestmark = pytest.mark.integration

PR = {
    "number": 7,
    "title": "Document the ledger export unstick steps",
    "body": "Clear export_locks for the batch, then re-queue it.",
    "state": "closed",
    "merged_at": "2026-10-05T09:00:00Z",
    "updated_at": "2026-10-05T09:00:00Z",
    "html_url": "https://github.com/northwind/ledger/pull/7",
    "user": {"login": "arjun-m"},
}


def github(prs: list[dict[str, Any]], status: int = 200) -> httpx.MockTransport:
    def respond(request: httpx.Request) -> httpx.Response:
        if status != 200:
            return httpx.Response(status)
        if request.url.path.endswith("/pulls"):
            return httpx.Response(200, json=prs)
        if request.url.path.endswith(("/reviews", "/commits", "/issues")):
            return httpx.Response(200, json=[])
        return httpx.Response(200, json={"name": "Arjun Mehta", "email": None})

    return httpx.MockTransport(respond)


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def graph() -> AsyncIterator[Graph]:
    settings = Settings(handovers_tenant="itest_connectors")
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


SETTINGS = Settings(github_token=SecretStr("t"), github_repos="northwind/ledger")
LLM_NONE = LLM(Settings(llm_provider="none"))


@pytest.mark.asyncio(loop_scope="module")
async def test_sync_writes_sources_and_moves_the_cursor(graph: Graph) -> None:
    async with httpx.AsyncClient(transport=github([PR])) as http:
        out = await sync.run(graph, LLM_NONE, SETTINGS, "github", http=http)
    assert out["status"] == "ok" and out["sources"] == 1
    src = await graph.one("source_get", {"id": "src:github:northwind-ledger-7"})
    assert src is not None
    state = await graph.one("connector_get", {"id": "github"})
    assert state is not None and state["cursor"] == "2026-10-05T09:00:00Z"

    # Nothing newer than the cursor: the next run writes nothing.
    async with httpx.AsyncClient(transport=github([PR])) as http:
        again = await sync.run(graph, LLM_NONE, SETTINGS, "github", http=http)
    assert again["sources"] == 0


@pytest.mark.asyncio(loop_scope="module")
async def test_a_refused_token_is_reported_and_keeps_the_cursor(graph: Graph) -> None:
    async with httpx.AsyncClient(transport=github([], status=401)) as http:
        out = await sync.run(graph, LLM_NONE, SETTINGS, "github", http=http)
    assert out["status"] == "error" and "refused the credentials" in (out["error"] or "")
    state = await graph.one("connector_get", {"id": "github"})
    assert state is not None and state["cursor"] == "2026-10-05T09:00:00Z"
    assert state["status"] == "error"


@pytest.mark.asyncio(loop_scope="module")
async def test_unconfigured_connectors_do_not_run(graph: Graph) -> None:
    with pytest.raises(sync.NotConfigured):
        await sync.run(graph, LLM_NONE, Settings(github_token=None), "github")
    with pytest.raises(sync.UnknownConnector):
        await sync.run(graph, LLM_NONE, SETTINGS, "myspace")


@pytest.mark.asyncio(loop_scope="module")
async def test_a_directory_sync_adds_people_and_who_they_report_to(graph: Graph) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "x"})
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "displayName": "Zoya Khan",
                        "mail": "zoya@northwind.example",
                        "jobTitle": "Growth Analyst",
                        "department": "Growth",
                        "accountEnabled": True,
                        "manager": {"mail": "aditi@northwind.example"},
                    }
                ]
            },
        )

    from connectors import REGISTRY
    from services import connector_config

    s = Settings(entra_tenant_id="t", entra_client_id="c", entra_client_secret=SecretStr("s"))
    # Only the active directory syncs.
    await connector_config.activate(graph, REGISTRY["entra"])
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        out = await sync.run(graph, LLM_NONE, s, "entra", http=http)
    assert out["status"] == "ok" and out["people"] == 1
    zoya = await graph.one("access_caller", {"emp": "emp:zoya"})
    assert zoya is not None and zoya["title"] == "Growth Analyst"
    aditi = await graph.one("access_caller", {"emp": "emp:aditi"})
    assert aditi is not None and "emp:zoya" in aditi["reports"]


@pytest.mark.asyncio(loop_scope="module")
async def test_settings_entered_in_the_app_are_encrypted_masked_and_used(graph: Graph) -> None:
    from connectors import REGISTRY
    from services import connector_config

    gh = REGISTRY["github"]
    await connector_config.save(
        graph,
        gh,
        {"github_token": "ghp_supersecret1234", "github_repos": "northwind/ledger"},
        "emp:meera",
    )
    stored = await graph.one("connector_config_get", {"id": "github"})
    assert stored is not None and "supersecret" not in stored["config"]  # encrypted at rest

    form = {f["key"]: f for f in await connector_config.describe(graph, Settings(), gh)}
    assert form["github_token"]["value"] == "••••1234" and form["github_token"]["source"] == "app"
    assert form["github_repos"]["value"] == "northwind/ledger"

    # A blank secret keeps the stored token; the plain field changes.
    await connector_config.save(
        graph, gh, {"github_token": "", "github_repos": "northwind/web"}, "emp:meera"
    )
    loaded = await connector_config.load(graph, "github")
    assert loaded == {"github_token": "ghp_supersecret1234", "github_repos": "northwind/web"}

    # A sync with no server-side settings at all runs on the app's values.
    seen: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("Authorization", ""))
        if request.url.path.endswith(("/pulls", "/commits", "/issues")):
            return httpx.Response(200, json=[])
        return httpx.Response(200, json={})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        out = await sync.run(graph, LLM_NONE, Settings(), "github", http=http)
    assert out["status"] == "ok" and seen and set(seen) == {"Bearer ghp_supersecret1234"}

    with pytest.raises(connector_config.InvalidConfig):
        await connector_config.save(graph, REGISTRY["jira"], {"jira_email": "a@b.c"}, "emp:meera")
    await connector_config.clear(graph, gh, "emp:meera")
    assert await connector_config.load(graph, "github") == {}


@pytest.mark.asyncio(loop_scope="module")
async def test_sessions_open_resolve_and_end(graph: Graph) -> None:
    from core import security
    from core.clock import now_ms

    nisha = await graph.one("employee_by_email", {"email": "nisha@northwind.example"})
    assert nisha is not None and nisha["id"] == "emp:nisha"
    assert await graph.one("employee_by_email", {"email": "nobody@example.com"}) is None

    token = security.new_token()
    now = now_ms()
    params = {"employee": "emp:nisha", "hash": security.token_hash(token), "now": now,
              "expires": now + 60_000, "id_token": "t"}  # fmt: skip
    await graph.run("session_create", params)
    row = await graph.one("session_get", {"hash": security.token_hash(token), "now": now})
    assert row is not None and row["employee"] == "emp:nisha"
    # The raw token is never stored; an expired session doesn't resolve.
    assert await graph.one("session_get", {"hash": token, "now": now}) is None
    later = await graph.one(
        "session_get", {"hash": security.token_hash(token), "now": now + 120_000}
    )
    assert later is None
    await graph.run("session_end", {"employee": "emp:nisha"})
    assert await graph.one("session_get", {"hash": security.token_hash(token), "now": now}) is None


@pytest.mark.asyncio(loop_scope="module")
async def test_the_platform_admin_signs_in_as_an_operator_not_an_employee(graph: Graph) -> None:
    from core import security
    from core.clock import now_ms
    from services.access import PLATFORM_ADMIN

    await graph.run(
        "operator_ensure",
        {"id": PLATFORM_ADMIN, "name": "Platform admin", "email": "admin@handovers.local"},
    )
    # Not in the directory: an operator never shows up as an employee.
    assert await graph.one("employee_by_email", {"email": "admin@handovers.local"}) is None
    token, now = security.new_token(), now_ms()
    await graph.run(
        "session_create",
        {"employee": PLATFORM_ADMIN, "hash": security.token_hash(token), "now": now,
         "expires": now + 60_000, "id_token": "t"},
    )  # fmt: skip
    row = await graph.one("session_get", {"hash": security.token_hash(token), "now": now})
    assert row is not None and row["employee"] == PLATFORM_ADMIN
    await graph.run("session_end", {"employee": PLATFORM_ADMIN})
    assert await graph.one("session_get", {"hash": security.token_hash(token), "now": now}) is None


@pytest.mark.asyncio(loop_scope="module")
async def test_one_directory_is_active_at_a_time_and_switching_keeps_settings(graph: Graph) -> None:
    from connectors import REGISTRY
    from services import connector_config

    entra, google = REGISTRY["entra"], REGISTRY["google_workspace"]
    s = Settings(entra_tenant_id="t", entra_client_id="c", entra_client_secret=SecretStr("s"))
    await connector_config.save(
        graph,
        entra,
        {"entra_tenant_id": "t", "entra_client_id": "c", "entra_client_secret": "s"},
        "t",
    )

    await connector_config.activate(graph, entra)
    assert await connector_config.active_in(graph, "directory") == "entra"
    await connector_config.activate(graph, google)
    assert await connector_config.active_in(graph, "directory") == "google_workspace"
    # The inactive directory keeps its settings but does not sync.
    assert (await connector_config.load(graph, "entra"))["entra_tenant_id"] == "t"
    with pytest.raises(sync.NotActive):
        await sync.run(graph, LLM_NONE, s, "entra")

    # Switching back needs no re-entry; deactivating leaves none active.
    await connector_config.activate(graph, entra)
    assert await connector_config.active_in(graph, "directory") == "entra"
    await connector_config.deactivate(graph, entra)
    assert await connector_config.active_in(graph, "directory") is None

    # Disconnecting makes a directory inactive and clears its settings.
    await connector_config.activate(graph, entra)
    await connector_config.clear(graph, entra, "t")
    assert await connector_config.active_in(graph, "directory") is None
    with pytest.raises(connector_config.InvalidConfig):
        await connector_config.activate(graph, REGISTRY["github"])  # work tools: no such state


@pytest.mark.asyncio(loop_scope="module")
async def test_the_last_test_of_saved_settings_is_kept_until_they_change(graph: Graph) -> None:
    from connectors import REGISTRY
    from services import connector_config

    await connector_config.record_test(
        graph, "slack", False, "slack.com refused the credentials (401)"
    )
    state = {r["id"]: r for r in await graph.read("connector_list", {})}["slack"]
    assert state["test_ok"] is False and "401" in state["test_message"] and state["tested_at"]

    await connector_config.save(
        graph, REGISTRY["slack"], {"slack_bot_token": "x", "slack_channels": "C1"}, "t"
    )
    state = {r["id"]: r for r in await graph.read("connector_list", {})}["slack"]
    assert state["test_ok"] is None and state["tested_at"] is None  # new settings, untested


@pytest.mark.asyncio(loop_scope="module")
async def test_a_work_tool_has_several_accounts_each_with_its_own_settings_and_teams(
    graph: Graph,
) -> None:
    from connectors import REGISTRY
    from services import connector_config

    gh = REGISTRY["github"]
    # The server's values (.env) apply to the first account only.
    server = Settings(github_token=SecretStr("server-token"), github_repos="northwind/ledger")
    await connector_config.save(
        graph, gh, {"github_token": "sales-token", "github_repos": "northwind/crm"}, "t",
        "github:sales-github", "Sales GitHub",
    )  # fmt: skip
    await connector_config.set_teams(graph, "github:sales-github", ["team:growth"])

    first = await connector_config.settings_for(graph, server, gh)
    sales = await connector_config.settings_for(graph, server, gh, "github:sales-github")
    assert first.github_repos == "northwind/ledger"
    assert sales.github_repos == "northwind/crm"
    assert sales.github_token is not None and sales.github_token.get_secret_value() == "sales-token"
    # A further account never inherits the server's token.
    bare = await connector_config.settings_for(graph, server, gh, "github:not-saved")
    assert not gh.configured(bare)

    accounts = await connector_config.accounts(graph, gh)
    assert [a["id"] for a in accounts][:1] == ["github"]
    sales_row = next(a for a in accounts if a["id"] == "github:sales-github")
    assert sales_row["label"] == "Sales GitHub" and sales_row["platform"] == "github"
    assert [t["id"] for t in sales_row["teams"]] == ["team:growth"]
    taken = {a["id"] for a in accounts}
    assert connector_config.new_account_id(gh, "Sales GitHub", taken) == "github:sales-github-2"

    # A sync of the account reads with its own token and records it as the source's origin.
    seen: list[str] = []
    recorded = github([PR])

    def respond(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("Authorization", ""))
        return recorded.handle_request(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        out = await sync.run(graph, LLM_NONE, server, "github:sales-github", http=http)
    assert out["status"] == "ok" and all(h.endswith("sales-token") for h in seen if h)

    # Disconnecting a further account removes it; the first account is untouched.
    await connector_config.clear(graph, gh, "t", "github:sales-github")
    assert "github:sales-github" not in {
        a["id"] for a in await connector_config.accounts(graph, gh)
    }

    # Disconnecting the first account clears its name and teams too.
    await connector_config.save(
        graph, gh, {"github_token": "t1", "github_repos": "a/b"}, "t", "github", "Product GitHub"
    )
    await connector_config.set_teams(graph, "github", ["team:engineering"])
    await connector_config.clear(graph, gh, "t")
    first = (await connector_config.accounts(graph, gh))[0]
    assert first["label"] is None and first["teams"] == []
