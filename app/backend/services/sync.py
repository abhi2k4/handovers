"""Run a connector: pull what changed since the last sync, extract facts, write through the review gate.

The sync state (cursor, counts, last error) is a `Connector` node in the tenant graph, so FalkorDB
stays the only store. A failed run keeps the old cursor and is retried in full next time.
"""

import re
from typing import Any

import httpx

from connectors import REGISTRY
from connectors.base import ConnectorError, Person
from core.clock import now_ms
from core.config import Settings
from core.graph import Graph
from core.llm import LLM
from ingestion import pipeline
from services import connector_config


class UnknownConnector(Exception):
    pass


class NotActive(Exception):
    """Another connector is the active one in this category (a directory): this one does not sync."""


class NotConfigured(Exception):
    pass


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]


async def write_people(graph: Graph, people: list[Person], system: str) -> int:
    now = now_ms()
    for p in people:
        await graph.run(
            "directory_upsert_person",
            {
                "email": p.email.lower(),
                "id": f"emp:{_slug(p.email.split('@')[0])}",
                "name": p.name,
                "title": p.title,
                "status": p.status,
                "team": f"team:{_slug(p.department)}" if p.department else "",
                "department": p.department or "",
                "system": system,
                "now": now,
            },
        )
    for p in people:
        if p.manager_email:
            await graph.run(
                "directory_set_manager",
                {"email": p.email.lower(), "manager": p.manager_email.lower()},
            )
    return len(people)


async def run(
    graph: Graph, llm: LLM, s: Settings, connector_id: str, http: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    # `connector_id` is an account: the platform id, or `github:<slug>` for a further account.
    connector = REGISTRY.get(connector_config.platform_of(connector_id))
    if connector is None:
        raise UnknownConnector(connector_id)
    s = await connector_config.settings_for(graph, s, connector, connector_id)
    if not connector.configured(s):
        raise NotConfigured(connector_id)
    state = await graph.one("connector_get", {"id": connector_id})
    if connector_config.exclusive(connector) and not (state or {}).get("active"):
        raise NotActive(connector_id)
    since = state.get("cursor") if state else None
    res = await pipeline.resolver(graph)
    result = {"id": connector_id, "sources": 0, "facts": 0, "review": 0, "people": 0}
    try:
        if http is not None:  # a caller-owned client (tests) stays open
            pulled = await connector.pull(http, s, res, since)
        else:
            async with httpx.AsyncClient(timeout=30) as client:
                pulled = await connector.pull(client, s, res, since)
        result["people"] = await write_people(graph, pulled.people, connector_id)
        if pulled.people:
            res = await pipeline.resolver(graph)  # new people can author the sources below
        for src in pulled.sources:
            if not src.facts and src.text.strip():
                src.facts, _ = await pipeline.extract(llm, src.text, res, src.author)
        written, queued = await pipeline.store(graph, pulled.sources, origin=connector_id)
        result |= {"sources": len(pulled.sources), "facts": written, "review": queued}
        status, error, cursor = "ok", None, pulled.cursor
    except ConnectorError as exc:
        status, error, cursor = "error", str(exc), since
    await graph.run(
        "connector_set",
        {
            "id": connector_id,
            "status": status,
            "error": error,
            "cursor": cursor,
            "now": now_ms(),
            "sources": result["sources"],
            "facts": result["facts"],
            "review": result["review"],
            "people": result["people"],
        },
    )
    return result | {"status": status, "error": error}
