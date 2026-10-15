"""Sign-in, sign-out and the signed-in person; Google and Microsoft sign-in setup for admins.

Backend-for-Frontend (core/keycloak.py): /login sends the browser to Keycloak, /callback exchanges
the code server-to-server and opens a session. The browser only ever holds an opaque httpOnly cookie;
the graph stores its hash. The sign-in attempt (state, nonce, PKCE verifier) rides in a short-lived
encrypted cookie between the two requests, so no server-side store is needed for it.
"""

import json
import logging
from typing import Annotated, Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse

from api.deps import SESSION_COOKIE, CallerDep, GraphDep, forbid
from core import keycloak, security
from core.clock import now_ms
from core.config import get_settings
from identity import REGISTRY as IDENTITY
from services import access, identity

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

ATTEMPT_COOKIE = "handovers_oidc"
ATTEMPT_MAX_AGE = 600
EXPIRED = "That sign-in link has expired. Please try again."
ADMIN = "Only the signed-in platform admin changes integrations and sign-in."


def _safe_next(path: str | None) -> str | None:
    """Only a same-site absolute path, so the parameter can't bounce someone to another site."""
    if (
        not path
        or not path.startswith("/")
        or path.startswith("//")
        or "\\" in path
        or "://" in path
    ):
        return None
    return path


def _known_provider(provider: str | None) -> str | None:
    """Only a registered provider is passed to Keycloak as a hint; anything else gets its page."""
    return provider if provider in IDENTITY else None


def _app(path: str) -> str:
    return get_settings().app_url(path)


def _refuse(message: str) -> RedirectResponse:
    r = RedirectResponse(_app(f"/login?{urlencode({'error': message})}"), 302)
    r.delete_cookie(ATTEMPT_COOKIE, path="/api/auth")
    return r


@router.get("/config")
async def config() -> dict[str, Any]:
    """What the login page offers. Public: it names providers, never their settings."""
    s = get_settings()
    providers: list[dict[str, Any]] = []
    available = False  # Keycloak configured AND reachable right now
    if s.sso_enabled:
        try:
            providers = [
                {"id": p["id"], "name": p["button"]}
                for p in await identity.providers(s)
                if p["configured"]
            ]
            available = True
        except (keycloak.KeycloakError, httpx.HTTPError) as exc:
            log.warning("Sign-in unavailable: %s", exc)
    return {
        "sso": s.sso_enabled,
        "available": available,
        "guest": s.allow_guest,
        "providers": providers,
    }


@router.get("/login")
async def login(
    provider: Annotated[str | None, Query()] = None, next: Annotated[str | None, Query()] = None
) -> RedirectResponse:
    s = get_settings()
    if not s.sso_enabled:
        raise HTTPException(404, "Sign-in is not set up")
    attempt = keycloak.begin_sign_in(s, _known_provider(provider))
    sealed = security.encrypt(
        json.dumps(
            {"state": attempt.state, "nonce": attempt.nonce, "verifier": attempt.verifier,
             "next": _safe_next(next)}
        )
    )  # fmt: skip
    r = RedirectResponse(attempt.url, 302)
    # Lax: the callback is a top-level navigation from Keycloak, which Strict would strip.
    r.set_cookie(ATTEMPT_COOKIE, sealed, max_age=ATTEMPT_MAX_AGE, httponly=True,
                 secure=s.session_cookie_secure, samesite="lax", path="/api/auth")  # fmt: skip
    return r


@router.get("/callback")
async def callback(
    graph: GraphDep,
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
    attempt_cookie: Annotated[str | None, Cookie(alias=ATTEMPT_COOKIE)] = None,
) -> RedirectResponse:
    s = get_settings()
    if error:
        return _refuse("Sign-in was cancelled.")
    if not code or not state or not attempt_cookie:
        return _refuse(EXPIRED)
    try:
        attempt = json.loads(security.decrypt(attempt_cookie))
    except (security.InvalidToken, ValueError):
        return _refuse(EXPIRED)
    if attempt.get("state") != state:
        return _refuse(EXPIRED)
    try:
        who = await keycloak.complete_sign_in(s, code, attempt["verifier"], attempt["nonce"])
    except keycloak.KeycloakError as exc:
        log.warning("Sign-in refused: %s", exc)
        return _refuse("Sign-in failed. Please try again.")
    if (
        who.email.lower() == s.platform_admin_email.lower()
        and s.platform_admin_password.get_secret_value()
    ):
        employee: dict[str, Any] | None = {"id": access.PLATFORM_ADMIN}
    else:
        employee = await graph.one("employee_by_email", {"email": who.email})
    if employee is None:
        # Nobody is created by signing in: the directory decides who works here.
        log.warning("Sign-in refused for an email not in the directory")
        return _refuse(f"{who.email} is not in the company directory.")

    token = security.new_token()
    now = now_ms()
    await graph.run(
        "session_create",
        {"employee": employee["id"], "hash": security.token_hash(token), "now": now,
         "expires": now + s.session_max_age_seconds * 1000, "id_token": who.id_token},
    )  # fmt: skip
    r = RedirectResponse(_app(attempt.get("next") or "/"), 302)
    r.delete_cookie(ATTEMPT_COOKIE, path="/api/auth")
    r.set_cookie(SESSION_COOKIE, token, max_age=s.session_max_age_seconds, httponly=True,
                 secure=s.session_cookie_secure, samesite="lax", path="/")  # fmt: skip
    return r


@router.get("/session")
async def session(request: Request, graph: GraphDep) -> dict[str, Any] | None:
    """The signed-in person, or null (guest or signed out)."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    row = await graph.one("session_get", {"hash": security.token_hash(token), "now": now_ms()})
    if row is None:
        return None
    return {"employee": row["employee"], "name": row["name"], "email": row["email"]}


@router.post("/logout")
async def logout(request: Request, response: Response, graph: GraphDep) -> dict[str, str | None]:
    """End every session of the caller here, and say where Keycloak ends its own."""
    s = get_settings()
    token = request.cookies.get(SESSION_COOKIE)
    id_token = None
    if token:
        row = await graph.one("session_get", {"hash": security.token_hash(token), "now": now_ms()})
        if row:
            id_token = row.get("id_token")
            await graph.run("session_end", {"employee": row["employee"]})
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"logout_url": keycloak.end_session_url(s, id_token) if s.sso_enabled else None}


# ---- admin: Google and Microsoft sign-in, people in Keycloak --------------------------------


@router.get("/providers")
async def list_providers(graph: GraphDep, caller: CallerDep) -> list[dict[str, Any]]:
    forbid(access.can_view_setup(caller), ADMIN)
    try:
        return await identity.providers(get_settings(), graph)
    except keycloak.KeycloakError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/providers/planned")
async def planned_providers(caller: CallerDep) -> list[dict[str, str]]:
    forbid(access.can_view_setup(caller), ADMIN)
    return identity.planned()


def _provider_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, identity.UnknownProvider):
        return HTTPException(404, "Unknown sign-in provider")
    if isinstance(exc, identity.NotEnabled):
        return HTTPException(409, "Sign-in (Keycloak) is not set up on this server")
    if isinstance(exc, identity.InvalidValues):
        return HTTPException(422, str(exc))
    return HTTPException(502, str(exc))


PROVIDER_ERRORS = (
    identity.UnknownProvider,
    identity.NotEnabled,
    identity.InvalidValues,
    keycloak.KeycloakError,
)


@router.post("/providers/{pid}/enable")
async def enable_provider(pid: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    """Make this the active sign-in provider, with its directory card's values.

    Every other provider is turned off (settings kept), so the login page offers one.
    """
    forbid(access.can_configure(caller), ADMIN)
    try:
        deactivated = await identity.enable(graph, get_settings(), pid)
    except PROVIDER_ERRORS as exc:
        raise _provider_errors(exc) from exc
    return {"id": pid, "deactivated": deactivated}


@router.delete("/providers/{pid}")
async def disable_provider(pid: str, caller: CallerDep) -> dict[str, str]:
    """Turn a sign-in provider off. Keycloak keeps its settings for when it is made active again."""
    forbid(access.can_configure(caller), ADMIN)
    try:
        await identity.disable(get_settings(), pid)
    except PROVIDER_ERRORS as exc:
        raise _provider_errors(exc) from exc
    return {"id": pid}


@router.post("/provision")
async def provision(graph: GraphDep, caller: CallerDep) -> dict[str, int]:
    """Give every employee in the graph a Keycloak account (disabled when they have left)."""
    forbid(access.can_configure(caller), ADMIN)
    try:
        return await identity.provision_people(graph, get_settings())
    except identity.NotEnabled as exc:
        raise HTTPException(409, "Sign-in (Keycloak) is not set up on this server") from exc
    except keycloak.KeycloakError as exc:
        raise HTTPException(502, str(exc)) from exc
