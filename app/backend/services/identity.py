"""People and sign-in providers in Keycloak, kept in step with the graph and the connectors.

The graph is the directory (seeded, or synced from Entra ID / an HR system). Every employee gets a
Keycloak account with their email, so signing in with Google or Microsoft links to the right person;
departed people are disabled. Nobody is created by signing in: an email the graph does not know is
refused (api/auth.py).
"""

from typing import Any

import httpx

from connectors import REGISTRY as CONNECTORS
from connectors.base import secret
from core import keycloak
from core.config import Settings
from core.graph import Graph
from identity import PLANNED
from identity import REGISTRY as IDENTITY
from identity.base import IdentityProvider
from services import access, connector_config


class NotEnabled(Exception):
    """Sign-in (Keycloak) is not set up on this server."""


class UnknownProvider(Exception):
    pass


class InvalidValues(Exception):
    """The message is shown to the admin."""


async def provision_people(graph: Graph, s: Settings) -> dict[str, int]:
    if not s.sso_enabled:
        raise NotEnabled
    people = await graph.read("people_directory", {})
    password = s.demo_user_password.get_secret_value() or None
    done = 0
    async with httpx.AsyncClient(timeout=20) as http:
        admin = await keycloak.Admin(s, http).login()
        for p in people:
            if not p.get("email"):
                continue
            await admin.upsert_user(
                p["email"].lower(), p["name"], p.get("status") != "departed", password
            )
            done += 1
    return {"people": done}


async def ensure_platform_admin(graph: Graph, s: Settings) -> bool:
    """The platform admin's `Operator` node and Keycloak account (email + password), at startup.

    Only when sign-in is on and PLATFORM_ADMIN_PASSWORD is set. Not an employee, so "Sync people"
    never touches it.
    """
    password = s.platform_admin_password.get_secret_value()
    if not s.sso_enabled or not password:
        return False
    email = s.platform_admin_email.lower()
    await graph.run(
        "operator_ensure", {"id": access.PLATFORM_ADMIN, "name": "Platform admin", "email": email}
    )
    async with httpx.AsyncClient(timeout=20) as http:
        admin = await keycloak.Admin(s, http).login()
        await admin.upsert_user(email, "Platform admin", True, password)
    return True


def _provider(pid: str) -> IdentityProvider:
    p = IDENTITY.get(pid)
    if p is None:
        raise UnknownProvider(pid)
    return p


async def providers(s: Settings, graph: Graph | None = None) -> list[dict[str, Any]]:
    """Every sign-in provider: whether it is the active one (on in Keycloak), and the redirect URI.

    With `graph`, also whether its directory card is connected (`ready`), so it can be made active.
    """
    existing: dict[str, dict[str, Any]] = {}
    if s.sso_enabled:
        async with httpx.AsyncClient(timeout=15) as http:
            existing = await (await keycloak.Admin(s, http).login()).providers()
    out = []
    for p in IDENTITY.values():
        kc = existing.get(p.id) or {}
        out.append(
            {
                "id": p.id,
                "name": p.name,
                "button": p.button,
                "guide": p.guide,
                "connector": p.connector,
                # Active: on in Keycloak. At most one is, so the login page offers one provider.
                "configured": bool(kc.get("enabled")),
                "ready": await _ready(graph, s, p) if graph is not None else None,
                "redirect_uri": f"{s.keycloak_issuer}/broker/{p.id}/endpoint",
            }
        )
    return out


def planned() -> list[dict[str, str]]:
    return [{"id": pid, "name": name} for pid, name in PLANNED.items()]


async def _register(s: Settings, p: IdentityProvider, values: dict[str, str]) -> None:
    if not s.sso_enabled:
        raise NotEnabled
    provider_id, config = p.keycloak(values)
    async with httpx.AsyncClient(timeout=15) as http:
        admin = await keycloak.Admin(s, http).login()
        await admin.upsert_provider(p.id, p.button, provider_id, config)


async def _values(graph: Graph, s: Settings, p: IdentityProvider) -> dict[str, str] | None:
    """The provider's values from its directory card, or None while that card is not connected."""
    connector = CONNECTORS[p.connector]
    effective = await connector_config.settings_for(graph, s, connector)
    if not connector.configured(effective):
        return None
    return {f.key: secret(getattr(effective, f.key, None)) for f in connector.fields}


async def _ready(graph: Graph, s: Settings, p: IdentityProvider) -> bool:
    return await _values(graph, s, p) is not None


async def _enabled(s: Settings) -> set[str]:
    """The sign-in providers that are on in Keycloak."""
    async with httpx.AsyncClient(timeout=15) as http:
        existing = await (await keycloak.Admin(s, http).login()).providers()
    return {alias for alias, rep in existing.items() if alias in IDENTITY and rep.get("enabled")}


async def enable_from_connector(graph: Graph, s: Settings, cid: str) -> list[str]:
    """After connector `cid` is saved: refresh its sign-in, or turn it on if none is active.

    One sign-in provider is active at a time, so a provider whose card was just saved is turned on
    only when no other one is; if another is active it stays off until made active. Returns the ids
    registered.
    """
    if not s.sso_enabled:
        raise NotEnabled
    on = await _enabled(s)
    done = []
    for p in IDENTITY.values():
        if p.connector != cid or (on and p.id not in on):
            continue
        values = await _values(graph, s, p)
        if values is not None:
            await _register(s, p, values)
            done.append(p.id)
    return done


async def enable(graph: Graph, s: Settings, pid: str) -> list[str]:
    """Make `pid` the active sign-in provider; every other one is turned off (settings kept).

    Returns the ids turned off.
    """
    p = _provider(pid)
    values = await _values(graph, s, p)
    if values is None:
        raise InvalidValues(f"Connect {CONNECTORS[p.connector].name} under Directory first")
    await _register(s, p, values)
    others = sorted((await _enabled(s)) - {p.id})
    for other in others:
        await disable(s, other)
    return others


async def disable(s: Settings, pid: str) -> None:
    """Turn a sign-in provider off. Keycloak keeps its settings and people's links to it."""
    if not s.sso_enabled:
        return
    async with httpx.AsyncClient(timeout=15) as http:
        admin = await keycloak.Admin(s, http).login()
        await admin.set_provider_enabled(_provider(pid).id, False)


async def disable_for_connector(s: Settings, cid: str) -> None:
    """The connector was disconnected: its sign-in goes too."""
    for p in IDENTITY.values():
        if p.connector == cid:
            await remove_provider(s, p.id)


async def remove_provider(s: Settings, pid: str) -> None:
    if not s.sso_enabled:
        return
    async with httpx.AsyncClient(timeout=15) as http:
        await (await keycloak.Admin(s, http).login()).remove_provider(_provider(pid).id)
