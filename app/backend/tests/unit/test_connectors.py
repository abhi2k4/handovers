"""Slack, Jira, Notion, HubSpot, Salesforce and Entra ID connectors against recorded responses."""

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from connectors import REGISTRY
from connectors.base import ConnectorError
from connectors.entra import Entra
from connectors.hubspot import HubSpot
from connectors.jira import Jira
from connectors.jira.connector import adf_text
from connectors.notion import Notion
from connectors.notion.connector import doc_type
from connectors.salesforce import Salesforce
from connectors.slack import Slack
from core.config import Settings
from ingestion.pipeline import Resolver

PEOPLE = [
    {"id": "emp:nisha", "name": "Nisha Verma", "email": "nisha@northwind.example"},
    {"id": "emp:arjun", "name": "Arjun Mehta", "email": "arjun@northwind.example"},
    {"id": "emp:rohan", "name": "Rohan Das", "email": "rohan@northwind.example"},
]
RES = Resolver(PEOPLE, [], [])

Route = Callable[[httpx.Request], Any]


def mock(routes: dict[str, Route]) -> httpx.AsyncClient:
    def respond(request: httpx.Request) -> httpx.Response:
        for prefix, fn in routes.items():
            if request.url.path.startswith(prefix):
                out = fn(request)
                return out if isinstance(out, httpx.Response) else httpx.Response(200, json=out)
        return httpx.Response(404)

    return httpx.AsyncClient(transport=httpx.MockTransport(respond))


@pytest.mark.asyncio
async def test_slack_threads_become_messages_by_author_with_repliers() -> None:
    s = Settings(slack_bot_token=SecretStr("xoxb-test"), slack_channels="C1")
    users = {"U1": "nisha@northwind.example", "U2": "rohan@northwind.example"}
    routes: dict[str, Route] = {
        "/api/conversations.history": lambda r: {
            "ok": True,
            "messages": [
                {"ts": "1760000000.000100", "user": "U1", "text": "Pausing Google Ads: ROAS under 1.8", "reply_count": 1},
                {"ts": "1760000001.000100", "user": "U2", "text": "ok"},
                {"ts": "1760000002.000100", "subtype": "channel_join", "text": "joined"},
            ],
        },
        "/api/conversations.replies": lambda r: {
            "ok": True,
            "messages": [{"ts": "1760000000.000100"}, {"user": "U2", "text": "Agreed, move it to Reels"}],
        },
        "/api/users.info": lambda r: {"ok": True, "user": {"profile": {"email": users[r.url.params["user"]]}}},
    }  # fmt: skip
    async with mock(routes) as http:
        pull = await Slack().pull(http, s, RES, None)
    assert len(pull.sources) == 1  # "ok" and the join notice are skipped
    m = pull.sources[0]
    assert m.kind == "Message" and m.author == "emp:nisha" and m.attendees == ["emp:rohan"]
    assert "Reels" in m.text and pull.cursor == "1760000000.000100"


@pytest.mark.asyncio
async def test_slack_error_codes_are_reported_without_secrets() -> None:
    s = Settings(slack_bot_token=SecretStr("xoxb-secret"), slack_channels="C1")
    routes: dict[str, Route] = {"/api/": lambda r: {"ok": False, "error": "not_in_channel"}}
    async with mock(routes) as http:
        with pytest.raises(ConnectorError) as err:
            await Slack().pull(http, s, RES, None)
    assert "not_in_channel" in str(err.value) and "xoxb" not in str(err.value)


@pytest.mark.asyncio
async def test_jira_issues_become_tickets_by_assignee() -> None:
    s = Settings(
        jira_base_url="https://northwind.atlassian.net",
        jira_email="bot@northwind.example",
        jira_api_token=SecretStr("t"),
        jira_projects="PAY",
    )
    seen: list[str] = []

    def search(r: httpx.Request) -> dict[str, Any]:
        seen.append(r.url.params["jql"])
        return {
            "issues": [
                {
                    "key": "PAY-12",
                    "fields": {
                        "summary": "Ledger export stuck again",
                        "description": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Cleared export_locks."}]}]},
                        "assignee": {"emailAddress": "arjun@northwind.example", "displayName": "Arjun Mehta"},
                        "updated": "2026-10-03T08:00:00.000+0000",
                        "resolutiondate": "2026-10-03T08:00:00.000+0000",
                    },
                }
            ]
        }  # fmt: skip

    async with mock({"/rest/api/3/search/jql": search}) as http:
        pull = await Jira().pull(http, s, RES, "2026-10-01T00:00:00.000+0000")
    t = pull.sources[0]
    assert t.id == "src:jira:pay-12" and t.kind == "Ticket" and t.status == "closed"
    assert t.author == "emp:arjun" and "export_locks" in t.text
    assert t.url == "https://northwind.atlassian.net/browse/PAY-12"
    assert 'project in ("PAY")' in seen[0] and 'updated >= "2026-10-01 00:00"' in seen[0]


def test_adf_text_flattens_paragraphs() -> None:
    doc = {"type": "doc", "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "Step one"}]},
        {"type": "paragraph", "content": [{"type": "text", "text": "Step two"}]},
    ]}  # fmt: skip
    assert adf_text(doc) == "Step one\nStep two"


@pytest.mark.asyncio
async def test_notion_pages_become_documents_by_creator() -> None:
    s = Settings(notion_token=SecretStr("secret_x"))
    page = {
        "id": "abc",
        "last_edited_time": "2026-10-04T10:00:00.000Z",
        "created_by": {"id": "u1"},
        "url": "https://notion.so/abc",
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": "Month-end UTM runbook"}]}
        },
    }
    routes: dict[str, Route] = {
        "/v1/search": lambda r: {"results": [page]},
        "/v1/blocks/abc/children": lambda r: {"results": [
            {"type": "numbered_list_item", "numbered_list_item": {"rich_text": [{"plain_text": "Export GA4 sessions"}]}},
            {"type": "image", "image": {}},
        ]},
        "/v1/users/u1": lambda r: {"name": "Nisha Verma", "person": {"email": "nisha@northwind.example"}},
    }  # fmt: skip
    async with mock(routes) as http:
        pull = await Notion().pull(http, s, RES, None)
    d = pull.sources[0]
    assert d.kind == "Document" and d.doc_type == "runbook" and d.author == "emp:nisha"
    assert "Export GA4 sessions" in d.text and pull.cursor == "2026-10-04T10:00:00.000Z"
    assert doc_type("ADR 7: pause Google Ads") == "adr" and doc_type("Team notes") == "wiki"


@pytest.mark.asyncio
async def test_hubspot_contacts_become_stakeholders_owned_by_the_rep() -> None:
    s = Settings(hubspot_token=SecretStr("pat-x"))
    routes: dict[str, Route] = {
        "/crm/v3/owners": lambda r: {"results": [{"id": "7", "email": "nisha@northwind.example"}]},
        "/crm/v3/objects/contacts/search": lambda r: {"results": [{"id": "1", "updatedAt": "2026-10-02T00:00:00Z",
            "properties": {"firstname": "Tom", "lastname": "Becker", "email": "tom@mixpanel.example", "company": "Mixpanel", "hubspot_owner_id": "7"}}]},
        "/crm/v3/objects/deals/search": lambda r: {"results": [{"id": "9", "updatedAt": "2026-10-03T00:00:00Z",
            "properties": {"dealname": "Mixpanel renewal", "dealstage": "contractsent", "amount": "12000", "hubspot_owner_id": "7"}}]},
    }  # fmt: skip
    async with mock(routes) as http:
        pull = await HubSpot().pull(http, s, RES, None)
    contact, deal = pull.sources
    fact = contact.facts[0]
    assert fact.kind == "stakeholder" and fact.org == "Mixpanel" and fact.people == ["emp:nisha"]
    assert fact.confidence >= 0.75  # passes the review gate: the CRM owner field is authoritative
    assert deal.author == "emp:nisha" and "renewal" in deal.text and deal.facts == []
    assert pull.cursor == "2026-10-03T00:00:00Z"


@pytest.mark.asyncio
async def test_salesforce_contacts_and_opportunities() -> None:
    s = Settings(
        salesforce_instance_url="https://northwind.my.salesforce.com",
        salesforce_token=SecretStr("t"),
    )

    def query(r: httpx.Request) -> dict[str, Any]:
        q = r.url.params.get("q", "")
        if "FROM Contact" in q:
            return {
                "records": [
                    {
                        "Id": "003A",
                        "Name": "Leena Rao",
                        "Email": "leena@acmebank.example",
                        "Account": {"Name": "AcmeBank"},
                        "Owner": {"Email": "arjun@northwind.example"},
                        "LastModifiedDate": "2026-10-01T00:00:00.000+0000",
                    }
                ]
            }
        return {"records": [{"Id": "006B", "Name": "AcmeBank settlement v2", "StageName": "Negotiation",
                             "Amount": 50000, "Owner": {"Email": "arjun@northwind.example"},
                             "LastModifiedDate": "2026-10-02T00:00:00.000+0000"}]}  # fmt: skip

    async with mock({"/services/data/": query}) as http:
        pull = await Salesforce().pull(http, s, RES, None)
    contact, deal = pull.sources
    assert contact.facts[0].org == "AcmeBank" and contact.facts[0].people == ["emp:arjun"]
    assert deal.author == "emp:arjun" and pull.cursor == "2026-10-02T00:00:00.000+0000"


@pytest.mark.asyncio
async def test_entra_users_become_people_with_managers() -> None:
    s = Settings(entra_tenant_id="tid", entra_client_id="cid", entra_client_secret=SecretStr("sec"))

    def token(r: httpx.Request) -> dict[str, Any]:
        assert b"grant_type=client_credentials" in r.content
        return {"access_token": "graph-token"}

    def users(r: httpx.Request) -> dict[str, Any]:
        assert r.headers["Authorization"] == "Bearer graph-token"
        return {"value": [
            {"displayName": "Nisha Verma", "mail": "nisha@northwind.example", "jobTitle": "Performance Marketing Manager",
             "department": "Growth", "accountEnabled": True, "manager": {"mail": "aditi@northwind.example"}},
            {"displayName": "Old Account", "mail": "old@northwind.example", "accountEnabled": False},
            {"displayName": "Guest", "userPrincipalName": "guest_x.com#EXT#@northwind.onmicrosoft.com"},
        ]}  # fmt: skip

    async with mock({"/tid/oauth2/v2.0/token": token, "/v1.0/users": users}) as http:
        pull = await Entra().pull(http, s, RES, None)
    assert [p.email for p in pull.people] == ["nisha@northwind.example", "old@northwind.example"]
    nisha, old = pull.people
    assert nisha.department == "Growth" and nisha.manager_email == "aditi@northwind.example"
    assert old.status == "departed" and pull.sources == []


def test_registry_lists_one_platform_per_kind() -> None:
    kinds = {c.category for c in REGISTRY.values()}
    assert {"chat", "code", "tickets", "docs", "crm", "directory"} <= kinds
    assert all(not c.configured(Settings()) for c in REGISTRY.values())  # nothing on by default


# ---- Test connection (check) ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_github_check_names_the_account_and_a_repo_it_cannot_read() -> None:
    from connectors.github import GitHub

    s = Settings(github_token=SecretStr("t"), github_repos="me/ok, me/missing")
    routes: dict[str, Route] = {
        "/user": lambda r: {"login": "jishan"},
        "/repos/me/ok/": lambda r: [],
        "/repos/me/missing/": lambda r: httpx.Response(404),
    }
    async with mock(routes) as http:
        with pytest.raises(ConnectorError) as err:
            await GitHub().check(http, s)
    assert "me/missing" in str(err.value)
    async with mock(routes) as http:
        ok = await GitHub().check(http, Settings(github_token=SecretStr("t"), github_repos="me/ok"))
    assert ok.startswith("Signed in as jishan")


@pytest.mark.asyncio
async def test_slack_check_says_when_the_app_is_not_in_a_channel() -> None:
    s = Settings(slack_bot_token=SecretStr("xoxb-x"), slack_channels="C1")
    routes: dict[str, Route] = {
        "/api/auth.test": lambda r: {"ok": True, "team": "Northwind", "user": "handovers"},
        "/api/conversations.history": lambda r: {"ok": False, "error": "not_in_channel"},
    }
    async with mock(routes) as http:
        with pytest.raises(ConnectorError, match="not_in_channel"):
            await Slack().check(http, s)


@pytest.mark.asyncio
async def test_entra_check_points_at_the_missing_permission() -> None:
    s = Settings(entra_tenant_id="t", entra_client_id="c", entra_client_secret=SecretStr("s"))
    routes: dict[str, Route] = {
        "/t/oauth2/v2.0/token": lambda r: {"access_token": "x"},
        "/v1.0/users": lambda r: httpx.Response(403),
    }
    async with mock(routes) as http:
        with pytest.raises(ConnectorError, match=r"User\.Read\.All"):
            await Entra().check(http, s)


@pytest.mark.asyncio
async def test_notion_check_warns_when_nothing_is_shared() -> None:
    routes: dict[str, Route] = {
        "/v1/users/me": lambda r: {"name": "Handovers"},
        "/v1/search": lambda r: {"results": []},
    }
    async with mock(routes) as http:
        msg = await Notion().check(http, Settings(notion_token=SecretStr("n")))
    assert "no pages are shared" in msg
