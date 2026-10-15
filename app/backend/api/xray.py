"""Graph X-ray: the queries behind a screen, the graph around its subject, and the project graph."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from api.deps import CallerDep, GraphDep, forbid
from core import trace
from services import access, tech_graph

router = APIRouter(prefix="/api/xray", tags=["xray"])

# Node kinds whose titles are knowledge content (hidden from HR unless leaver or manager).
CONTENT = {"Knowledge", "Decision", "Procedure", "Claim", "Gap", "InterviewAnswer"}
MAX_NODES = 40


@router.get("/subgraph")
async def subgraph(id: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    """The node `id` and up to 40 direct neighbours, as nodes and edges for the UI."""
    redact = False
    if caller is not None:
        if id.startswith("emp:"):
            forbid(access.can_view_person(caller, id), "Not visible to you.")
            redact = caller.id != id and not access.is_manager_of(caller, id)
        elif id.startswith("ho:"):
            h = await graph.one("handover_get", {"id": id})
            if h is None:
                raise HTTPException(404, "Not found")
            forbid(access.can_view_handover(caller, h["employee_id"]), "Not part of this handover.")
            redact = not access.can_read_answers(caller, h["employee_id"])
        else:
            held = await graph.one("xray_holds", {"emp": caller.id, "id": id})
            forbid(bool(held and held["n"]), "Only items in your own memory.")

    own = caller is None or caller.id == id
    rows = await graph.read("xray_neighbourhood", {"id": id, "limit": MAX_NODES, "self": own})
    if not rows:
        raise HTTPException(404, "Not found")

    def node(nid: str, labels: list[str], label: str) -> dict[str, Any]:
        kind = next(
            (lbl for lbl in labels if lbl not in {"Knowledge", "Source"}),
            labels[0] if labels else "",
        )
        hidden = redact and nid != id and bool(CONTENT & set(labels))
        # Nodes without a name or title (e.g. handovers) are shown by their kind, not a raw id.
        return {"id": nid, "kind": kind, "label": kind if hidden or label == nid else label}

    first = rows[0]
    nodes = {first["id"]: node(first["id"], first["labels"], first["label"])}
    edges = []
    for r in rows:
        if r["mid"] is None:
            continue
        nodes.setdefault(r["mid"], node(r["mid"], r["mlabels"], r["mlabel"]))
        src, dst = (r["rel_from"], r["mid"] if r["rel_from"] == id else id)
        edges.append({"source": src, "target": dst, "type": r["rel"]})
    return {
        "root": id,
        "nodes": list(nodes.values()),
        "edges": edges,
        "truncated": len(rows) >= MAX_NODES,
    }


# Before /{trace_id}, which would otherwise take "project" as a trace id.
@router.get("/project")
async def project(request: Request) -> dict[str, Any]:
    """How Handovers is built: the project graph from FalkorDB (services/tech_graph.py).

    Public, like the query catalogue: it describes the software, never a company's data.
    """
    graph = request.app.state.project_graph
    try:
        return await tech_graph.read(graph)
    except Exception as exc:  # FalkorDB down: the button says so instead of a 500
        raise HTTPException(503, "The project graph is not available right now.") from exc


@router.get("/{trace_id}")
async def get_trace(trace_id: str, request: Request) -> dict[str, Any]:
    """The named queries one API request ran, with their Cypher text."""
    t = trace.get(trace_id)
    if t is None:
        raise HTTPException(404, "Trace expired or unknown")
    catalog = request.app.state.graph.catalog
    return {
        **t,
        "queries": [{**q, "cypher": catalog.get(q["name"], q["label"])} for q in t["queries"]],
    }
