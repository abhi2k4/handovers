"""Successor ramp-up plan: generate, review, approve, tick off (product-strategy section 11)."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.deps import CallerDep, GraphDep, forbid
from core.clock import now_ms
from services import access, ramp

router = APIRouter(prefix="/api", tags=["ramp"])

MANAGER_ONLY = "Only the leaver's manager can change or approve the ramp-up plan."


async def _handover(graph: GraphDep, hid: str) -> dict[str, Any]:
    h = await graph.one("handover_get", {"id": hid})
    if h is None:
        raise HTTPException(404, "Not found")
    return h


@router.get("/handovers/{hid}/ramp")
async def get_ramp(hid: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    h = await _handover(graph, hid)
    plan = await ramp.get(graph, hid)
    status = plan["status"] if plan else None
    forbid(
        access.can_view_ramp(caller, h["employee_id"], h.get("successor_id"), status)
        or (caller is not None and caller.id == h.get("successor_id")),
        "Not part of this handover.",
    )
    if caller is not None and caller.id == h.get("successor_id") and status != "approved":
        # The successor learns only that a plan is on its way, not the draft.
        return {"status": status or "none", "items": [], "done": 0, "total": 0}
    return plan or {"status": "none", "items": [], "done": 0, "total": 0}


@router.post("/handovers/{hid}/ramp", status_code=201)
async def generate_ramp(hid: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    h = await _handover(graph, hid)
    forbid(
        access.can_run_handover(caller, h["employee_id"]),
        "Only HR or the leaver's manager can do this.",
    )
    try:
        return await ramp.generate(graph, hid)
    except ramp.NoSuccessor as exc:
        raise HTTPException(409, "Choose a successor before creating a ramp-up plan.") from exc


@router.post("/handovers/{hid}/ramp/approve")
async def approve_ramp(hid: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    h = await _handover(graph, hid)
    forbid(access.can_approve(caller, h["employee_id"]), MANAGER_ONLY)
    rows = await graph.run(
        "ramp_approve", {"handover": hid, "now": now_ms(), "by": caller.id if caller else "system"}
    )
    if not rows:
        raise HTTPException(409, "There is no draft plan to approve.")
    plan = await ramp.get(graph, hid)
    assert plan is not None
    return plan


class ItemIn(BaseModel):
    week: int | None = Field(default=None, ge=1, le=3)
    removed: bool | None = None
    done: bool | None = None


@router.post("/ramp-items/{iid}")
async def update_item(iid: str, body: ItemIn, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    item = await graph.one("ramp_item_get", {"id": iid})
    if item is None:
        raise HTTPException(404, "Not found")
    h = await _handover(graph, item["handover"])
    if body.done is not None:
        forbid(
            access.can_tick_ramp(caller, h.get("successor_id")),
            "Only the successor ticks items off.",
        )
        if item["status"] != "approved":
            raise HTTPException(409, "The plan is not approved yet.")
        rows = await graph.run("ramp_item_done", {"id": iid, "done": body.done, "now": now_ms()})
    else:
        forbid(access.can_approve(caller, h["employee_id"]), MANAGER_ONLY)
        if item["status"] != "draft":
            raise HTTPException(409, "An approved plan can no longer be edited.")
        rows = await graph.run(
            "ramp_item_edit", {"id": iid, "week": body.week, "removed": body.removed}
        )
    if not rows:
        raise HTTPException(409, "Not changed.")
    return rows[0]
