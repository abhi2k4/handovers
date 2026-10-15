"""The successor's companion."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.deps import CallerDep, GraphDep, LLMDep, forbid
from services import access, companion

router = APIRouter(prefix="/api/companion", tags=["companion"])


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    session: str | None = None


@router.post("/{emp}/ask")
async def ask(
    emp: str, body: AskIn, graph: GraphDep, llm: LLMDep, caller: CallerDep
) -> dict[str, Any]:
    forbid(access.can_act_as(caller, emp), "You can only ask from your own memory.")
    return await companion.ask(graph, llm, emp, body.question, body.session)


@router.get("/{emp}/profile")
async def profile(emp: str, graph: GraphDep, caller: CallerDep, llm: LLMDep) -> dict[str, Any]:
    """Whose memory this is, what it holds, and questions worth asking it."""
    from services import analysis

    forbid(access.can_act_as(caller, emp), "You can only ask from your own memory.")
    person = await analysis.person(graph, emp)
    if person is None:
        raise HTTPException(404, "Person not found")
    items = companion.digest(person)
    count = {
        k: sum(1 for i in items if i["kind"] in kinds)
        for k, kinds in {
            "knowledge": ("Decision", "Procedure", "Claim"),
            "work": ("Responsibility",),
            "people": ("Relationship",),
            "accounts": ("Account",),
        }.items()
    }
    return {
        "id": person["id"],
        "name": person["name"],
        "title": person.get("title"),
        "team": person.get("team"),
        "counts": count,
        "only_you": sum(1 for i in items if i.get("only_you")),
        "inherited": sum(1 for i in items if i.get("inherited")),
        "suggestions": companion.suggestions(items),
        "model": llm.model,
    }
