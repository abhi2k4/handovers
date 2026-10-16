"""GitHub: commits, pull requests and issues, from the REST API with a fine-grained token.

Each commit becomes a `Commit` source by its author, each pull request a `PullRequest` (reviewers as
attendees), each issue a `Ticket` (by assignee). Extraction then finds the responsibilities,
decisions and skills they show. People are matched to employees by commit email, profile name or
login.
"""

from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from connectors.base import Connector, ConnectorError, Field, Pull, csv_list, secret
from connectors.http import get_json
from core.config import Settings
from ingestion.pipeline import Resolver
from ingestion.schema import SourceIn

API = "https://api.github.com"
PAGE = 50
COMMITS = 100  # per repo and sync; the first sync starts from the newest

# Resolves a GitHub login to an employee id (cached per sync).
Who = Callable[[str | None], Awaitable[str | None]]


def _headers(s: Settings) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {secret(s.github_token)}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


class GitHub(Connector):
    id = "github"
    name = "GitHub"
    category = "code"
    fields = (
        Field("github_token", "Fine-grained access token", secret=True, placeholder="github_pat_...",
              hint="Read-only: Contents, Issues and Pull requests, on the repositories below."),
        Field("github_repos", "Repositories", placeholder="northwind/payments, northwind/web",
              hint="owner/repo, comma-separated."),
    )  # fmt: skip

    async def check(self, http: httpx.AsyncClient, s: Settings) -> str:
        headers = _headers(s)
        user = await get_json(http, f"{API}/user", headers=headers)
        repos = csv_list(s.github_repos)
        for repo in repos:
            for path, permission in (
                ("commits", "Contents"),
                ("issues", "Issues"),
                ("pulls", "Pull requests"),
            ):
                try:
                    await get_json(
                        http, f"{API}/repos/{repo}/{path}", headers=headers, params={"per_page": 1}
                    )
                except ConnectorError as exc:
                    raise ConnectorError(
                        f"Can't read {path} in {repo}: check the name and that the token has "
                        f"access to it ({permission}: Read-only)."
                    ) from exc
        return (
            f"Signed in as {user.get('login')}. Can read commits, issues and pull requests "
            f"in {len(repos)} repo(s)."
        )

    async def pull(
        self, http: httpx.AsyncClient, s: Settings, res: Resolver, since: str | None
    ) -> Pull:
        headers = _headers(s)
        people: dict[str, str | None] = {}

        async def who(login: str | None) -> str | None:
            if not login:
                return None
            if login not in people:
                user = await get_json(http, f"{API}/users/{login}", headers=headers)
                people[login] = (
                    res.person(user.get("email"))
                    or res.person(user.get("name"))
                    or res.person(login)
                )
            return people[login]

        out = Pull(cursor=since)
        for repo in csv_list(s.github_repos):
            await self._pull_requests(http, headers, repo, since, who, out)
            await self._commits(http, headers, repo, since, who, res, out)
            await self._issues(http, headers, repo, since, who, out)
        return out

    async def _commits(
        self,
        http: httpx.AsyncClient,
        headers: dict[str, str],
        repo: str,
        since: str | None,
        who: Who,
        res: Resolver,
        out: Pull,
    ) -> None:
        """One source per commit, by its author. The first sync reads the newest COMMITS only."""
        params: dict[str, Any] = {"per_page": COMMITS}
        if since:
            params["since"] = since
        commits = await get_json(
            http, f"{API}/repos/{repo}/commits", headers=headers, params=params
        )
        for c in commits:
            if len(c.get("parents") or []) > 1:
                continue  # merge commits repeat what the merged work already says
            info = c["commit"]
            git_author = info.get("author") or {}
            when = (info.get("committer") or git_author).get("date") or ""
            if since and when <= since:
                continue  # `since` is inclusive
            message = (info.get("message") or "").strip()
            out.sources.append(
                SourceIn(
                    id=f"src:github:{repo.replace('/', '-')}-commit-{c['sha'][:12]}",
                    kind="Commit",
                    system="github",
                    title=f"{repo}@{c['sha'][:7]} {message.splitlines()[0][:90] if message else ''}",
                    text=message,
                    occurred_at=when,
                    author=res.person(git_author.get("email"))
                    or res.person(git_author.get("name"))
                    or await who((c.get("author") or {}).get("login")),
                    url=c.get("html_url"),
                )
            )
            out.cursor = max(out.cursor or "", when)

    async def _issues(
        self,
        http: httpx.AsyncClient,
        headers: dict[str, str],
        repo: str,
        since: str | None,
        who: Who,
        out: Pull,
    ) -> None:
        """Issues as tickets, by assignee (or whoever opened them)."""
        params: dict[str, Any] = {"state": "all", "sort": "updated", "direction": "desc"}
        params |= {"per_page": PAGE} | ({"since": since} if since else {})
        issues = await get_json(http, f"{API}/repos/{repo}/issues", headers=headers, params=params)
        for i in issues:
            if "pull_request" in i or (since and i["updated_at"] <= since):
                continue  # the issues API also lists pull requests; those are read above
            person = (i.get("assignee") or i.get("user") or {}).get("login")
            out.sources.append(
                SourceIn(
                    id=f"src:github:{repo.replace('/', '-')}-issue-{i['number']}",
                    kind="Ticket",
                    system="github",
                    title=f"{repo}#{i['number']} {i['title']}",
                    text=f"{i['title']}\n\n{i.get('body') or ''}".strip(),
                    occurred_at=i.get("closed_at") or i["updated_at"],
                    author=await who(person),
                    url=i.get("html_url"),
                    status="closed" if i.get("state") == "closed" else "open",
                )
            )
            out.cursor = max(out.cursor or "", i["updated_at"])

    async def _pull_requests(
        self,
        http: httpx.AsyncClient,
        headers: dict[str, str],
        repo: str,
        since: str | None,
        who: Who,
        out: Pull,
    ) -> None:
        """Pull requests by author, with reviewers as attendees."""
        prs: list[dict[str, Any]] = await get_json(
            http,
            f"{API}/repos/{repo}/pulls",
            headers=headers,
            params={"state": "all", "sort": "updated", "direction": "desc", "per_page": PAGE},
        )
        for pr in prs:
            updated = pr["updated_at"]
            if since and updated <= since:
                break  # sorted newest first: everything after this was synced before
            reviews = await get_json(
                http, f"{API}/repos/{repo}/pulls/{pr['number']}/reviews", headers=headers
            )
            reviewers = {await who(r.get("user", {}).get("login")) for r in reviews}
            author = await who(pr.get("user", {}).get("login"))
            out.sources.append(
                SourceIn(
                    id=f"src:github:{repo.replace('/', '-')}-{pr['number']}",
                    kind="PullRequest",
                    system="github",
                    title=f"{repo}#{pr['number']} {pr['title']}",
                    text=f"{pr['title']}\n\n{pr.get('body') or ''}".strip(),
                    occurred_at=pr.get("merged_at") or updated,
                    author=author,
                    attendees=sorted(r for r in reviewers if r and r != author),
                    url=pr.get("html_url"),
                    status="merged" if pr.get("merged_at") else pr.get("state"),
                )
            )
            out.cursor = max(out.cursor or "", updated)
