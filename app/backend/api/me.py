"""Who am I, demo personas, and the KPI dashboard."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.deps import CallerDep, GraphDep, LLMDep, forbid
from services import access, copilot, kpis

router = APIRouter(prefix="/api", tags=["me"])

# Fields every participant of a handover may see (no knowledge content).
SUMMARY = (
    "id",
    "status",
    "effective_at",
    "employee_id",
    "employee",
    "title",
    "manager_id",
    "manager",
    "successor_id",
    "successor",
)


@router.get("/me")
async def me(caller: CallerDep, graph: GraphDep) -> dict[str, Any] | None:
    """The current "View as" person, roles, home screen and the handovers they take part in.

    Null when no persona is chosen (unrestricted mode).
    """
    if caller is None:
        return None
    out = access.describe(caller)
    for key in ("leaving", "succeeding", "managing"):
        rows = [await graph.one("handover_get", {"id": hid}) for hid in out[key]]
        out[key] = [{k: r.get(k) for k in SUMMARY} for r in rows if r]
    return out


@router.get("/personas")
async def personas(graph: GraphDep) -> list[dict[str, Any]]:
    """Demo identities for the "View as" switcher."""
    return await access.personas(graph)


@router.get("/kpis")
async def get_kpis(graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    forbid(access.can_view_org(caller), "Organisation KPIs are for HR and leadership.")
    return await kpis.build(graph)


class CopilotIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    page: str = "home"


@router.post("/copilot")
async def ask_copilot(
    body: CopilotIn, graph: GraphDep, llm: LLMDep, caller: CallerDep
) -> dict[str, Any]:
    """The search bar on every page: grounded in the app guide and the caller's own memory."""
    return await copilot.ask(graph, llm, caller, body.question, body.page)


@router.get("/copilot/suggestions")
async def copilot_suggestions(page: str = "home") -> list[str]:
    return copilot.suggestions(page)
