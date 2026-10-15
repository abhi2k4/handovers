"""People and their work memory."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.deps import CallerDep, GraphDep, forbid
from services import access, analysis

router = APIRouter(prefix="/api/people", tags=["people"])


@router.get("")
async def list_people(graph: GraphDep, caller: CallerDep) -> list[dict[str, Any]]:
    people = await analysis.people(graph)
    if caller is None or access.can_view_org(caller):
        return people
    # Managers see their own team; everyone else only themselves.
    visible = set(caller.reports) | {caller.id}
    return [p for p in people if p["id"] in visible]


@router.get("/{emp}")
async def get_person(emp: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    forbid(access.can_view_person(caller, emp), "You can see your own memory and your team's.")
    p = await analysis.person(graph, emp)
    if p is None:
        raise HTTPException(404, "Person not found")
    if caller is None or caller.id == emp:
        return p
    p = access.hide_private(p)  # nobody else sees private or personal items
    if not access.is_manager_of(caller, emp):
        return access.redact_person(p)  # HR: what they do and control, not what they know
    return p


class PrivateIn(BaseModel):
    private: bool


@router.post("/{emp}/knowledge/{kid}/private")
async def set_private(
    emp: str, kid: str, body: PrivateIn, graph: GraphDep, caller: CallerDep
) -> dict[str, Any]:
    forbid(access.can_act_as(caller, emp), "Only the person can change their privacy settings.")
    rows = await graph.run("person_set_private", {"emp": emp, "id": kid, "private": body.private})
    if not rows:
        raise HTTPException(404, "Not in this person's memory")
    return rows[0]


@router.get("/{emp}/simulate")
async def simulate_departure(emp: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    forbid(
        access.can_view_org(caller) or access.is_manager_of(caller, emp),
        "Only HR, leadership or the person's manager can simulate a departure.",
    )
    """What would be left with no one if this person left tomorrow (sole holders only)."""
    p = await analysis.person(graph, emp)
    if p is None:
        raise HTTPException(404, "Person not found")
    return {
        "id": p["id"],
        "name": p["name"],
        "responsibilities": [
            {"id": r["id"], "title": r["title"], "cadence": r["cadence"]}
            for r in p["responsibilities"]
            if not r["co_owners"]
        ],
        "accounts": [
            {"id": a["id"], "title": a["name"]}
            for a in p["accounts"]
            if a["role"] in ("admin", "owner") and not a["other_admins"]
        ],
        "relationships": [
            {"id": s["id"], "title": f"{s['name']}, {s['org']}"}
            for s in p["stakeholders"]
            if not s["other_contacts"]
        ],
        "knowledge": [
            {"id": k["id"], "title": k["title"], "kind": k["kind"]}
            for k in p["knowledge"]
            if not k["others"] and k["sensitivity"] != "personal" and k["status"] != "superseded"
        ],
    }
