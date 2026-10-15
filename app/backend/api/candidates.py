"""Candidates for a leaver's vacancy: imported from a job board's export, screened, alerted."""

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.deps import CallerDep, GraphDep, LLMDep, forbid
from core.clock import now_ms
from core.config import get_settings
from core.graph import Graph
from core.llm import LLM
from services import access, alerts, candidates, generators
from services import handover as svc

router = APIRouter(prefix="/api", tags=["candidates"])
SAMPLE = "seed/northwind/samples/workindia-candidates.csv"


class ImportIn(BaseModel):
    csv: str
    source: str = "WorkIndia"


async def _import(
    graph: Graph, llm: LLM, hid: str, text: str, source: str, caller: access.Caller | None
) -> dict[str, Any]:
    try:
        h = await svc.get(graph, hid)
    except svc.NotFound as exc:
        raise HTTPException(404, "Not found") from exc
    forbid(access.can_run_handover(caller, h["employee_id"]), "Only HR or the manager hires.")
    rows = candidates.parse(text)
    if not rows:
        raise HTTPException(422, "No candidates found. The file needs a Name column.")
    kit = await generators.build_screening(graph, llm, h["employee_id"])
    screened = candidates.screen(rows, kit["criteria"], hid, source)
    before = {c["id"] for c in await graph.read("candidate_list", {"handover": hid})}
    await graph.run("candidate_add", {"handover": hid, "rows": screened, "now": now_ms()})
    strong = [
        c
        for c in screened
        if c["id"] not in before and c["must_total"] and c["must_met"] == c["must_total"]
    ]
    hr = [r["id"] for r in await access.hr_people(graph)]
    for c in strong:
        for to in hr:
            await alerts.notify(
                graph,
                "candidate",
                to,
                f"{c['name']}: all {c['must_total']} must-haves",
                f"Applied on {source} for {h['title']} ({h['employee'].split(' ')[0]}'s role)."
                f" {c['city']}. Call {c['phone']}.",
                [{"id": f"open:/handovers/{hid}?tab=candidates", "label": "Open candidates"}],
                f"/handovers/{hid}?tab=candidates",
                hid,
            )
    return {
        "imported": len(screened),
        "new": len([c for c in screened if c["id"] not in before]),
        "strong": len(strong),
    }


@router.post("/handovers/{hid}/candidates")
async def import_candidates(
    hid: str, body: ImportIn, graph: GraphDep, llm: LLMDep, caller: CallerDep
) -> dict[str, Any]:
    return await _import(graph, llm, hid, body.csv, body.source, caller)


@router.post("/handovers/{hid}/candidates/sample")
async def import_sample(
    hid: str, graph: GraphDep, llm: LLMDep, caller: CallerDep
) -> dict[str, Any]:
    """The synthetic WorkIndia export that ships with the sample company."""
    text = (get_settings().graph_dir / SAMPLE).read_text(encoding="utf-8")
    return await _import(graph, llm, hid, text, "WorkIndia", caller)


@router.get("/handovers/{hid}/candidates")
async def list_candidates(hid: str, graph: GraphDep, caller: CallerDep) -> list[dict[str, Any]]:
    h = await graph.one("handover_get", {"id": hid})
    if h is None:
        raise HTTPException(404, "Not found")
    forbid(access.can_run_handover(caller, h["employee_id"]), "Only HR or the manager hires.")
    rows = await graph.read("candidate_list", {"handover": hid})
    return [r | {"verdicts": json.loads(r["verdicts"] or "[]")} for r in rows]
