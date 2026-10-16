"""GitHub connector against recorded API responses (no network)."""

import json
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from connectors.github import GitHub
from core.config import Settings
from ingestion.pipeline import Resolver

PEOPLE = [
    {"id": "emp:arjun", "name": "Arjun Mehta", "email": "arjun@northwind.example"},
    {"id": "emp:rohan", "name": "Rohan Das", "email": "rohan@northwind.example"},
]

PRS = [
    {
        "number": 42,
        "title": "Retry settlement calls with idempotency keys",
        "body": "Caps retries at 3 so AcmeBank doesn't double-post.",
        "state": "closed",
        "merged_at": "2026-10-01T10:00:00Z",
        "updated_at": "2026-10-01T10:00:00Z",
        "html_url": "https://github.com/northwind/payments/pull/42",
        "user": {"login": "arjun-m"},
    },
    {
        "number": 41,
        "title": "Old change",
        "body": None,
        "state": "closed",
        "merged_at": None,
        "updated_at": "2026-09-01T10:00:00Z",
        "html_url": "https://github.com/northwind/payments/pull/41",
        "user": {"login": "arjun-m"},
    },
]


COMMITS = [
    {
        "sha": "a1b2c3d4e5f60718293a",
        "parents": [{"sha": "p1"}],
        "html_url": "https://github.com/northwind/payments/commit/a1b2c3d",
        "author": {"login": "arjun-m"},
        "commit": {
            "message": "Cap settlement retries at 3\n\nAcmeBank double-posts beyond that.",
            "author": {"name": "Arjun", "email": "arjun@northwind.example"},
            "committer": {"date": "2026-10-02T09:00:00Z"},
        },
    },
    {
        "sha": "ffff000011112222",
        "parents": [{"sha": "p1"}, {"sha": "p2"}],
        "commit": {"message": "Merge pull request #42", "author": {}, "committer": {"date": "2026-10-02T10:00:00Z"}},
    },
]  # fmt: skip

ISSUES = [
    {"number": 7, "title": "Ledger export stuck", "body": "Clear export_locks.", "state": "closed",
     "closed_at": "2026-10-03T08:00:00Z", "updated_at": "2026-10-03T08:00:00Z",
     "assignee": {"login": "arjun-m"}, "html_url": "https://github.com/northwind/payments/issues/7"},
    {"number": 42, "title": "A pull request", "pull_request": {}, "updated_at": "2026-10-01T10:00:00Z"},
]  # fmt: skip


def handler(seen: list[str]) -> Any:
    def respond(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        assert request.headers["Authorization"] == "Bearer test-token"
        path = request.url.path
        if path == "/repos/northwind/payments/pulls":
            return httpx.Response(200, json=PRS)
        if path == "/repos/northwind/payments/commits":
            return httpx.Response(200, json=COMMITS)
        if path == "/repos/northwind/payments/issues":
            return httpx.Response(200, json=ISSUES)
        if path.endswith("/reviews"):
            return httpx.Response(200, json=[{"user": {"login": "rohan-d"}}])
        if path == "/users/arjun-m":
            return httpx.Response(200, json={"name": "Arjun Mehta", "email": None})
        if path == "/users/rohan-d":
            return httpx.Response(200, json={"name": None, "email": "rohan@northwind.example"})
        return httpx.Response(404, text=json.dumps({"message": "Not Found"}))

    return respond


def settings() -> Settings:
    return Settings(github_token=SecretStr("test-token"), github_repos="northwind/payments")


@pytest.mark.asyncio
async def test_pull_requests_become_sources_by_their_author() -> None:
    seen: list[str] = []
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler(seen))) as http:
        pull = await GitHub().pull(
            http, settings(), Resolver(PEOPLE, [], []), since="2026-09-15T00:00:00Z"
        )

    assert [s.id for s in pull.sources] == [
        "src:github:northwind-payments-42",
        "src:github:northwind-payments-commit-a1b2c3d4e5f6",  # the merge commit is skipped
        "src:github:northwind-payments-issue-7",  # the pull request in the issue list is skipped
    ]
    pr, commit, issue = pull.sources
    assert commit.kind == "Commit" and commit.author == "emp:arjun"  # by commit email
    assert commit.title == "northwind/payments@a1b2c3d Cap settlement retries at 3"
    assert issue.kind == "Ticket" and issue.status == "closed" and issue.author == "emp:arjun"
    assert pr.kind == "PullRequest" and pr.system == "github" and pr.status == "merged"
    assert pr.author == "emp:arjun" and pr.attendees == ["emp:rohan"]
    assert "idempotency" in pr.text
    assert pull.cursor == "2026-10-03T08:00:00Z"
    # Older than the cursor: its reviews are never fetched.
    assert "/repos/northwind/payments/pulls/41/reviews" not in seen


def test_configured_only_with_token_and_repos() -> None:
    assert GitHub().configured(settings())
    assert not GitHub().configured(Settings(github_token=SecretStr("x"), github_repos=""))
    assert not GitHub().configured(Settings(github_token=None, github_repos="a/b"))
