"""Jira Cloud: issues updated since the last sync, one `Ticket` source each, by assignee.

REST API v3 with basic auth (account email + API token). Descriptions arrive as Atlassian Document
Format and are flattened to text for extraction. Recurring fixes surface through the gap rules once
the same kind of ticket keeps landing on one person.
"""

from datetime import datetime
from typing import Any

import httpx

from connectors.base import Connector, ConnectorError, Field, Pull, csv_list, secret
from connectors.http import get_json
from core.config import Settings
from ingestion.pipeline import Resolver
from ingestion.schema import SourceIn

FIELDS = "summary,description,status,assignee,reporter,updated,labels,resolutiondate"


def adf_text(node: Any) -> str:
    """Plain text from an Atlassian Document Format tree."""
    if isinstance(node, dict):
        if node.get("type") == "text":
            return str(node.get("text", ""))
        parts = [adf_text(c) for c in node.get("content", [])]
        sep = "\n" if node.get("type") in ("doc", "bulletList", "orderedList") else ""
        return sep.join(p for p in parts if p)
    return ""


def _jql_time(iso: str) -> str:
    """Jira JQL accepts "yyyy-MM-dd HH:mm"; the cursor is Jira's own ISO timestamp."""
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")


class Jira(Connector):
    id = "jira"
    name = "Jira"
    category = "tickets"
    fields = (
        Field("jira_base_url", "Site URL", placeholder="https://your-site.atlassian.net"),
        Field("jira_email", "Account email", placeholder="you@company.com"),
        Field("jira_api_token", "API token", secret=True, hint="id.atlassian.com, Security, API tokens."),
        Field("jira_projects", "Project keys", placeholder="PAY, GROW"),
    )  # fmt: skip

    async def check(self, http: httpx.AsyncClient, s: Settings) -> str:
        base = s.jira_base_url.rstrip("/")
        auth = (s.jira_email, secret(s.jira_api_token))
        me = await get_json(http, f"{base}/rest/api/3/myself", auth=auth)
        projects = csv_list(s.jira_projects)
        for key in projects:
            try:
                await get_json(http, f"{base}/rest/api/3/project/{key}", auth=auth)
            except ConnectorError as exc:
                raise ConnectorError(f"Can't see project {key}: check the key and access.") from exc
        return f"Signed in as {me.get('displayName')}. Can see {len(projects)} project(s)."

    async def pull(
        self, http: httpx.AsyncClient, s: Settings, res: Resolver, since: str | None
    ) -> Pull:
        base = s.jira_base_url.rstrip("/")
        auth = (s.jira_email, secret(s.jira_api_token))
        projects = ", ".join(f'"{p}"' for p in csv_list(s.jira_projects))
        jql = f"project in ({projects})"
        if since:
            jql += f' AND updated >= "{_jql_time(since)}"'
        jql += " ORDER BY updated ASC"

        out = Pull(cursor=since)
        token: str | None = None
        while True:
            params: dict[str, Any] = {"jql": jql, "fields": FIELDS, "maxResults": 100}
            if token:
                params["nextPageToken"] = token
            page = await get_json(http, f"{base}/rest/api/3/search/jql", auth=auth, params=params)
            for issue in page.get("issues", []):
                f = issue["fields"]
                if since and f["updated"] <= since:
                    continue  # JQL is minute-precise; skip what the last sync already saw
                person = f.get("assignee") or f.get("reporter") or {}
                author = res.person(person.get("emailAddress")) or res.person(
                    person.get("displayName")
                )
                description = adf_text(f.get("description"))
                out.sources.append(
                    SourceIn(
                        id=f"src:jira:{issue['key'].lower()}",
                        kind="Ticket",
                        system="jira",
                        title=f"{issue['key']} {f['summary']}",
                        text=f"{f['summary']}\n\n{description}".strip(),
                        occurred_at=f.get("resolutiondate") or f["updated"],
                        author=author,
                        url=f"{base}/browse/{issue['key']}",
                        status="closed" if f.get("resolutiondate") else "open",
                    )
                )
                out.cursor = max(out.cursor or "", f["updated"])
            token = page.get("nextPageToken")
            if not token:
                return out
