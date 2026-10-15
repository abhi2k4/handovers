"""Shared request dependencies."""

from dataclasses import replace
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request

from core.clock import now_ms
from core.config import get_settings
from core.graph import Graph
from core.llm import LLM
from core.security import token_hash
from services.access import Caller, load_caller


def get_graph(request: Request) -> Graph:
    graph: Graph = request.app.state.graph
    return graph


def get_llm(request: Request) -> LLM:
    llm: LLM = request.app.state.llm
    return llm


GraphDep = Annotated[Graph, Depends(get_graph)]
LLMDep = Annotated[LLM, Depends(get_llm)]


SESSION_COOKIE = "handovers_session"


async def get_caller(
    request: Request, x_view_as: Annotated[str | None, Header()] = None
) -> Caller | None:
    """Who is asking.

    1. A signed-in session (Keycloak, api/auth.py) always wins; the View-as header is then ignored,
       so nobody signed in can act as someone else.
    2. Otherwise the demo "View as" header, when guests are allowed (ALLOW_GUEST, the live link for
       judges). It is not authentication.
    3. Otherwise unrestricted (None, local development), unless sign-in is set up and guests are
       not allowed: then the request is refused.
    """
    graph = request.app.state.graph
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        row = await graph.one("session_get", {"hash": token_hash(token), "now": now_ms()})
        if row is not None:
            return await load_caller(graph, row["employee"])
    s = get_settings()
    if not x_view_as or not s.allow_guest:
        if s.sso_enabled and not s.allow_guest:
            raise HTTPException(401, "Sign in to continue.")
        return None
    caller = await load_caller(graph, x_view_as)
    if caller is None:
        raise HTTPException(401, f"Unknown person for View as: {x_view_as}")
    return replace(caller, guest=True)


CallerDep = Annotated[Caller | None, Depends(get_caller)]


def forbid(allowed: bool, message: str) -> None:
    if not allowed:
        raise HTTPException(403, message)
