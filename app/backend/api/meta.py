"""App metadata, the query catalogue (for judges), and demo reset."""

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from api.deps import CallerDep, GraphDep, LLMDep, forbid
from core.clock import now_ms
from core.config import get_settings

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/meta")
async def meta(graph: GraphDep, llm: LLMDep) -> dict[str, Any]:
    stats = await graph.read("graph_stats", {})
    return {
        "company": "Northwind",
        "now": now_ms(),
        "model": llm.model,
        "graph": {r["label"]: r["n"] for r in stats},
        "reset_enabled": get_settings().allow_reset,
    }


@router.get("/queries")
async def queries(graph: GraphDep) -> list[dict[str, str]]:
    return [{"name": n, "cypher": graph.catalog.source(n)} for n in graph.catalog.names()]


@router.get("/demo/answers")
async def demo_answers() -> dict[str, str]:
    """Scripted exit-interview answers for the sample company (demo deployments only)."""
    if not get_settings().allow_reset:
        return {}
    path = get_settings().graph_dir / "seed" / "northwind" / "interview.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


@router.post("/demo/reset")
async def reset(request: Request, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    from services import access

    if not get_settings().allow_reset:
        raise HTTPException(403, "Reset is disabled")
    forbid(access.can_configure(caller), "Only the platform admin reloads the sample company.")
    from seed.load import bootstrap, load, open_scenario

    client = request.app.state.falkordb
    if await client.graph_exists():
        await client.graph().delete()
    await bootstrap(graph)
    stats = await load(graph)
    await open_scenario(graph)
    return {"sources": stats.sources, "facts": stats.facts}


@router.get("/dashboard")
async def dashboard(graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    from services import access

    forbid(access.can_view_org(caller), "The organisation overview is for HR and leadership.")
    from services import dashboard as dash

    return await dash.build(graph)
