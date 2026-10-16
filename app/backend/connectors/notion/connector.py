"""Notion: pages shared with the integration, one `Document` source each, by their creator.

Uses an internal integration secret (Notion: Settings > Connections > Develop integrations); share
each page or teamspace with the integration. Block text is flattened for extraction. Titles that
name a runbook, decision record or job description set the document type, which the gap rules use.
"""

from typing import Any

import httpx

from connectors.base import Connector, Field, Pull, secret
from connectors.http import get_json, post_json
from core.config import Settings
from ingestion.pipeline import Resolver
from ingestion.schema import SourceIn

API = "https://api.notion.com/v1"
TEXT_BLOCKS = {
    "paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item",
    "numbered_list_item", "to_do", "quote", "callout", "toggle", "code",
}  # fmt: skip
DOC_TYPES = {
    "runbook": "runbook",
    "adr": "adr",
    "decision": "adr",
    "sop": "sop",
    "job description": "jd",
}


def _plain(rich: list[dict[str, Any]]) -> str:
    return "".join(r.get("plain_text", "") for r in rich)


def page_title(page: dict[str, Any]) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            return _plain(prop.get("title", [])) or "Untitled"
    return "Untitled"


def doc_type(title: str) -> str:
    low = title.lower()
    return next((t for word, t in DOC_TYPES.items() if word in low), "wiki")


class Notion(Connector):
    id = "notion"
    name = "Notion"
    category = "docs"
    fields = (
        Field("notion_token", "Integration secret", secret=True, placeholder="ntn_...",
              hint="Share each page with the integration: page menu, Connections."),
    )  # fmt: skip

    async def check(self, http: httpx.AsyncClient, s: Settings) -> str:
        headers = {
            "Authorization": f"Bearer {secret(s.notion_token)}",
            "Notion-Version": "2022-06-28",
        }
        me = await get_json(http, f"{API}/users/me", headers=headers)
        found = await post_json(
            http,
            f"{API}/search",
            headers=headers,
            json={"filter": {"property": "object", "value": "page"}, "page_size": 1},
        )
        if not found.get("results"):
            return f"Connected as {me.get('name')}, but no pages are shared with it yet."
        return f"Connected as {me.get('name')}. Pages are shared with it."

    async def pull(
        self, http: httpx.AsyncClient, s: Settings, res: Resolver, since: str | None
    ) -> Pull:
        headers = {
            "Authorization": f"Bearer {secret(s.notion_token)}",
            "Notion-Version": "2022-06-28",
        }
        people: dict[str, str | None] = {}

        async def who(user_id: str | None) -> str | None:
            if not user_id:
                return None
            if user_id not in people:
                u = await get_json(http, f"{API}/users/{user_id}", headers=headers)
                people[user_id] = res.person((u.get("person") or {}).get("email")) or res.person(
                    u.get("name")
                )
            return people[user_id]

        out = Pull(cursor=since)
        body = {
            "filter": {"property": "object", "value": "page"},
            "sort": {"direction": "descending", "timestamp": "last_edited_time"},
            "page_size": 50,
        }
        found = await post_json(http, f"{API}/search", headers=headers, json=body)
        for page in found.get("results", []):
            edited = page["last_edited_time"]
            if since and edited <= since:
                break  # newest first
            blocks = await get_json(
                http,
                f"{API}/blocks/{page['id']}/children",
                headers=headers,
                params={"page_size": 100},
            )
            lines = [
                _plain(b[b["type"]].get("rich_text", []))
                for b in blocks.get("results", [])
                if b.get("type") in TEXT_BLOCKS
            ]
            title = page_title(page)
            kind = doc_type(title)
            out.sources.append(
                SourceIn(
                    id=f"src:notion:{page['id']}",
                    kind="Document",
                    system="notion",
                    title=title,
                    text="\n".join([title, *[line for line in lines if line]]),
                    occurred_at=edited,
                    author=await who((page.get("created_by") or {}).get("id")),
                    url=page.get("url"),
                    doc_type=kind,
                )
            )
            out.cursor = max(out.cursor or "", edited)
        return out
