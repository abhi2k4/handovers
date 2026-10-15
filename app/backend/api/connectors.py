"""Data connectors: which platforms are connected, their settings form, their sync state, "Sync now"."""

import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.deps import CallerDep, GraphDep, LLMDep, forbid
from connectors import PLANNED, REGISTRY
from connectors.base import Connector, ConnectorError, present
from core.config import get_settings
from core.graph import Graph
from core.keycloak import KeycloakError
from services import access, connector_config, identity, sync

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/connectors", tags=["connectors"])

ADMIN = "Only the signed-in platform admin changes integrations and sign-in."


def _connector(cid: str) -> Connector:
    """The platform of an account id (`github` or `github:<slug>`)."""
    c = REGISTRY.get(connector_config.platform_of(cid))
    if c is None:
        raise HTTPException(404, "Unknown connector")
    return c


async def _account(graph: Graph, cid: str) -> Connector:
    """The platform of an existing account: a further account must have been added first."""
    c = _connector(cid)
    if cid != c.id and cid not in {a["id"] for a in await connector_config.accounts(graph, c)}:
        raise HTTPException(404, "Unknown account")
    return c


@router.get("")
async def list_connectors(graph: GraphDep, caller: CallerDep) -> list[dict[str, Any]]:
    forbid(access.can_view_setup(caller), ADMIN)
    s = get_settings()
    state = {r["id"]: r for r in await graph.read("connector_list", {})}
    out = []
    for c in REGISTRY.values():
        effective = await connector_config.settings_for(graph, s, c)
        accounts = []
        for a in await connector_config.accounts(graph, c):
            a_settings = await connector_config.settings_for(graph, s, c, a["id"])
            accounts.append(
                {
                    "id": a["id"],
                    "label": a.get("label"),
                    "teams": a.get("teams") or [],
                    "configured": c.configured(a_settings),
                    "fields": await connector_config.describe(graph, s, c, a["id"]),
                    "state": state.get(a["id"]),
                }
            )
        out.append(
            {
                "id": c.id,
                "name": c.name,
                "category": c.category,
                "configured": c.configured(effective),
                # One active at a time in this category (a directory): see `state.active`.
                "exclusive": connector_config.exclusive(c),
                # The connect form: labels and hints, with secrets masked (never sent in full).
                "fields": await connector_config.describe(graph, s, c),
                "state": state.get(c.id),
                # Work tools: every connected account (the first is this connector's own id).
                "accounts": accounts,
            }
        )
    return out


@router.get("/teams")
async def teams(graph: GraphDep, caller: CallerDep) -> list[dict[str, Any]]:
    """Teams a work-tool account can serve."""
    forbid(access.can_view_setup(caller), ADMIN)
    return await graph.read("team_list", {})


@router.get("/planned")
async def planned(caller: CallerDep) -> list[dict[str, str]]:
    """Platforms the Integrations page shows as coming soon."""
    forbid(access.can_view_setup(caller), ADMIN)
    return [{"id": cid, "name": name, "category": cat} for cid, (name, cat) in PLANNED.items()]


class ConfigIn(BaseModel):
    values: dict[str, str]
    # Work tools only: what the account is called, and the teams it serves (None keeps them).
    label: str | None = None
    teams: list[str] | None = None


class AccountIn(ConfigIn):
    label: str


@router.post("/{cid}/accounts")
async def add_account(
    cid: str, body: AccountIn, graph: GraphDep, caller: CallerDep
) -> dict[str, Any]:
    """Connect another account of a work tool (a second GitHub, a sales Jira)."""
    forbid(access.can_configure(caller), ADMIN)
    c = _connector(cid)
    if cid != c.id or connector_config.exclusive(c):
        raise HTTPException(409, f"{c.name} is connected once; it has no further accounts.")
    label = body.label.strip()
    existing = await connector_config.accounts(graph, c)
    if not label:
        raise HTTPException(422, "Name the account, e.g. Sales Jira.")
    if label.lower() in {str(a.get("label") or "").lower() for a in existing}:
        raise HTTPException(422, f"There is already an account called {label}.")
    account = connector_config.new_account_id(c, label, {a["id"] for a in existing})
    try:
        await connector_config.save(
            graph, c, body.values, caller.id if caller else "system", account, label
        )
    except connector_config.InvalidConfig as exc:
        raise HTTPException(422, str(exc)) from exc
    await connector_config.set_teams(graph, account, body.teams or [])
    return {"id": account, "configured": True}


@router.put("/{cid}/config")
async def save_config(
    cid: str, body: ConfigIn, graph: GraphDep, caller: CallerDep
) -> dict[str, Any]:
    forbid(access.can_configure(caller), ADMIN)
    c = await _account(graph, cid)
    try:
        await connector_config.save(
            graph, c, body.values, caller.id if caller else "system", cid, body.label
        )
    except connector_config.InvalidConfig as exc:
        raise HTTPException(422, str(exc)) from exc
    if body.teams is not None and not connector_config.exclusive(c):
        await connector_config.set_teams(graph, cid, body.teams)
    # The first directory connected becomes the active one; a second is kept, inactive, until an
    # admin switches to it.
    active = False
    if connector_config.exclusive(c) and not await connector_config.active_in(graph, c.category):
        await connector_config.activate(graph, c)
        active = True
    # A directory that also signs people in refreshes that sign-in, or turns it on when no other
    # provider is on. Saving never fails on it: the Sign-in tab says so and offers "Make active".
    sign_in: list[str] = []
    try:
        sign_in = await identity.enable_from_connector(graph, get_settings(), cid)
    except identity.NotEnabled:
        pass
    except (KeycloakError, httpx.HTTPError) as exc:
        log.warning("Sign-in not turned on for %s: %s", cid, exc)
    return {"id": cid, "configured": True, "active": active, "sign_in": sign_in}


@router.post("/{cid}/test")
async def test_connection(
    cid: str, body: ConfigIn, graph: GraphDep, caller: CallerDep
) -> dict[str, Any]:
    """Check the form's values against the platform with one read-only call; nothing is saved.

    With no values (every field blank) it tests the saved settings, and the result is kept for
    the card.
    """
    forbid(access.can_configure(caller), ADMIN)
    # Not `_account`: an account being added has no id yet; the form tests `<platform>:new`, which
    # starts from no saved values (never the first account's).
    c = _connector(cid)
    saved = not any(v.strip() for v in body.values.values())
    try:
        s = await connector_config.preview(graph, get_settings(), c, body.values, cid)
    except connector_config.InvalidConfig as exc:
        raise HTTPException(422, str(exc)) from exc
    if not c.configured(s):
        missing = [f.label for f in c.fields if not present(getattr(s, f.key, None))]
        return {"ok": False, "message": f"Fill in: {', '.join(missing) or 'every field'}."}
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            result = {"ok": True, "message": await c.check(http, s)}
    except ConnectorError as exc:
        result = {"ok": False, "message": str(exc)}
    if saved:
        await connector_config.record_test(graph, cid, bool(result["ok"]), str(result["message"]))
    return result


@router.post("/{cid}/activate")
async def activate(cid: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    """Make this the active directory; the one active before becomes inactive, settings kept."""
    forbid(access.can_configure(caller), ADMIN)
    c = _connector(cid)
    if not connector_config.exclusive(c):
        raise HTTPException(409, f"{c.name} has no active or inactive state; connect it to use it.")
    if not c.configured(await connector_config.settings_for(graph, get_settings(), c)):
        raise HTTPException(409, f"Connect {c.name} first.")
    previous = await connector_config.active_in(graph, c.category)
    await connector_config.activate(graph, c)
    return {"id": cid, "active": True, "deactivated": previous if previous != cid else None}


@router.post("/{cid}/deactivate")
async def deactivate(cid: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    """Stop using this directory: it keeps its settings but no longer syncs."""
    forbid(access.can_configure(caller), ADMIN)
    c = _connector(cid)
    if not connector_config.exclusive(c):
        raise HTTPException(409, f"{c.name} has no active or inactive state.")
    await connector_config.deactivate(graph, c)
    return {"id": cid, "active": False}


@router.delete("/{cid}/config")
async def disconnect(cid: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    forbid(access.can_configure(caller), ADMIN)
    c = await _account(graph, cid)
    await connector_config.clear(graph, c, caller.id if caller else "system", cid)
    if cid != c.id:
        return {"id": cid, "configured": False}  # a further account: removed, no sign-in tied to it
    try:
        await identity.disable_for_connector(get_settings(), cid)
    except (KeycloakError, httpx.HTTPError) as exc:
        log.warning("Sign-in not turned off for %s: %s", cid, exc)
    return {"id": cid, "configured": False}


@router.post("/{cid}/sync")
async def sync_now(cid: str, graph: GraphDep, llm: LLMDep, caller: CallerDep) -> dict[str, Any]:
    forbid(access.can_configure(caller), ADMIN)
    try:
        return await sync.run(graph, llm, get_settings(), cid)
    except sync.UnknownConnector as exc:
        raise HTTPException(404, "Unknown connector") from exc
    except sync.NotConfigured as exc:
        raise HTTPException(409, "Not connected yet: enter its settings first.") from exc
    except sync.NotActive as exc:
        raise HTTPException(
            409, "Another directory is active. Make this one active to sync it."
        ) from exc
