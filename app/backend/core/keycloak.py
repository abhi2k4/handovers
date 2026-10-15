"""Keycloak: sign-in (authorization code + PKCE, Backend-for-Frontend) and its admin API.

The backend is the only OAuth client. The browser is sent to Keycloak, comes back to
/api/auth/callback with a code, and the backend exchanges it server-to-server and verifies the ID
token against Keycloak's published keys. No token reaches the browser: it gets an httpOnly session
cookie (api/auth.py). The admin API (service account) provisions people and sign-in providers.
Modelled on the kenz-intent backend's keycloak.py.
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

from core.config import Settings


class KeycloakError(Exception):
    """Sign-in or an admin call failed; the message names no secret."""


@dataclass(frozen=True)
class SignInRequest:
    state: str
    nonce: str
    verifier: str
    url: str


@dataclass(frozen=True)
class Identity:
    email: str
    name: str
    id_token: str


def begin_sign_in(s: Settings, provider: str | None = None) -> SignInRequest:
    """A fresh state, nonce and PKCE verifier, and the Keycloak URL to send the browser to."""
    state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(3))
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    query = {
        "client_id": s.keycloak_client_id,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": s.oidc_redirect_uri,
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if provider:
        # Straight to that provider (a registered alias), skipping Keycloak's own page.
        query["kc_idp_hint"] = provider
    return SignInRequest(
        state,
        nonce,
        verifier,
        f"{s.keycloak_issuer}/protocol/openid-connect/auth?{urlencode(query)}",
    )


async def _token(http: httpx.AsyncClient, s: Settings, data: dict[str, str]) -> dict[str, Any]:
    try:
        r = await http.post(
            f"{s.keycloak_internal_realm_url}/protocol/openid-connect/token",
            data=data,
            auth=(s.keycloak_client_id, s.keycloak_client_secret.get_secret_value()),
        )
    except httpx.HTTPError as exc:
        raise KeycloakError("Could not reach Keycloak") from exc
    if r.status_code != 200:
        raise KeycloakError(f"Keycloak refused the token request ({r.status_code})")
    payload: dict[str, Any] = r.json()
    return payload


async def complete_sign_in(
    s: Settings, code: str, verifier: str, nonce: str, http: httpx.AsyncClient | None = None
) -> Identity:
    if http is None:
        async with httpx.AsyncClient(timeout=15) as client:
            return await complete_sign_in(s, code, verifier, nonce, client)
    tokens = await _token(
        http,
        s,
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": s.oidc_redirect_uri,
            "code_verifier": verifier,
        },
    )
    id_token = tokens.get("id_token")
    if not isinstance(id_token, str):
        raise KeycloakError("Keycloak returned no ID token")
    claims = await verify(s, id_token, http)
    if claims.get("nonce") != nonce:
        raise KeycloakError("The sign-in response did not match this attempt")
    email = str(claims.get("email") or claims.get("preferred_username") or "")
    if not email:
        raise KeycloakError("The account has no email address")
    return Identity(email=email.lower(), name=str(claims.get("name") or email), id_token=id_token)


def end_session_url(s: Settings, id_token: str | None) -> str:
    params = {
        "client_id": s.keycloak_client_id,
        # Registered in the realm as exactly APP_PUBLIC_URL/login; the site forwards it to the app.
        "post_logout_redirect_uri": f"{s.app_public_url.rstrip('/')}/login",
    }
    if id_token:
        params["id_token_hint"] = id_token
    return f"{s.keycloak_issuer}/protocol/openid-connect/logout?{urlencode(params)}"


# ---- ID token verification ----------------------------------------------------------------

_keys: dict[str, jwt.PyJWK] = {}


async def _signing_key(s: Settings, kid: str, http: httpx.AsyncClient) -> jwt.PyJWK:
    if kid not in _keys:  # unknown key id: refetch, which is how a key rotation is picked up
        try:
            r = await http.get(f"{s.keycloak_internal_realm_url}/protocol/openid-connect/certs")
        except httpx.HTTPError as exc:
            raise KeycloakError("Could not reach Keycloak") from exc
        for key in jwt.PyJWKSet.from_dict(r.json()).keys:
            if key.key_id:
                _keys[key.key_id] = key
    if kid not in _keys:
        raise KeycloakError("The token was signed with a key Keycloak does not publish")
    return _keys[kid]


async def verify(s: Settings, token: str, http: httpx.AsyncClient) -> dict[str, Any]:
    """Claims of an ID token once its signature, issuer, audience and expiry hold."""
    try:
        kid = jwt.get_unverified_header(token).get("kid")
    except jwt.PyJWTError as exc:
        raise KeycloakError("That is not a token") from exc
    if not isinstance(kid, str):
        raise KeycloakError("The token names no signing key")
    key = await _signing_key(s, kid, http)
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            key=key.key,
            algorithms=[key.algorithm_name],
            audience=s.keycloak_client_id,
            issuer=s.keycloak_issuer,
            options={"require": ["exp", "iat", "sub"]},
            leeway=30,  # container clocks drift
        )
    except jwt.PyJWTError as exc:
        raise KeycloakError(f"The token was rejected: {exc}") from exc
    return claims


# ---- admin API (service account) ------------------------------------------------------------


class Admin:
    """The realm's admin REST API, as the backend's service account."""

    def __init__(self, s: Settings, http: httpx.AsyncClient) -> None:
        self.s, self.http = s, http
        self.base = f"{s.keycloak_url.rstrip('/')}/admin/realms/{s.keycloak_realm}"
        self.headers: dict[str, str] = {}

    async def login(self) -> "Admin":
        tokens = await _token(self.http, self.s, {"grant_type": "client_credentials"})
        self.headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        return self

    async def call(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            r = await self.http.request(
                method, f"{self.base}{path}", headers=self.headers, **kwargs
            )
        except httpx.HTTPError as exc:
            raise KeycloakError("Could not reach Keycloak") from exc
        if r.status_code >= 400 and r.status_code != 404:
            raise KeycloakError(f"Keycloak admin {method} {path.split('?')[0]}: {r.status_code}")
        return r

    async def providers(self) -> dict[str, dict[str, Any]]:
        r = await self.call("GET", "/identity-provider/instances")
        return {p["alias"]: p for p in r.json()} if r.status_code == 200 else {}

    async def upsert_provider(
        self, alias: str, display_name: str, provider_id: str, config: dict[str, str]
    ) -> None:
        """Create or update a sign-in provider. Config keys left out (a blank secret) are kept."""
        existing = (await self.providers()).get(alias)
        if existing and existing.get("providerId") != provider_id:
            # Keycloak cannot change a provider's type in place (e.g. built-in "microsoft" to an
            # OIDC provider pinned to one tenant).
            await self.remove_provider(alias)
            existing = None
        body = {
            "alias": alias,
            "providerId": provider_id,
            "displayName": display_name,
            "enabled": True,
            "trustEmail": True,
            "storeToken": False,
            # Link to an existing account with the same email; nobody new is created on sign-in.
            "firstBrokerLoginFlowAlias": "first broker login",
            "config": (existing or {}).get("config", {}) | config,
        }
        if existing:
            await self.call("PUT", f"/identity-provider/instances/{alias}", json=body)
        else:
            await self.call("POST", "/identity-provider/instances", json=body)

    async def set_provider_enabled(self, alias: str, enabled: bool) -> None:
        """Turn a sign-in provider on or off, keeping its configuration and people's links to it."""
        existing = (await self.providers()).get(alias)
        if existing and bool(existing.get("enabled")) != enabled:
            await self.call(
                "PUT", f"/identity-provider/instances/{alias}", json=existing | {"enabled": enabled}
            )

    async def remove_provider(self, alias: str) -> None:
        await self.call("DELETE", f"/identity-provider/instances/{alias}")

    async def upsert_user(self, email: str, name: str, enabled: bool, password: str | None) -> None:
        r = await self.call("GET", "/users", params={"email": email, "exact": "true"})
        first, _, last = name.partition(" ")
        body: dict[str, Any] = {
            "username": email,
            "email": email,
            "firstName": first,
            "lastName": last or first,
            "enabled": enabled,
            "emailVerified": True,
            "attributes": {"handovers_source": ["graph"]},
        }
        if password:
            body["credentials"] = [{"type": "password", "value": password, "temporary": False}]
        users = r.json() if r.status_code == 200 else []
        if users:
            await self.call("PUT", f"/users/{users[0]['id']}", json=body)
        else:
            await self.call("POST", "/users", json=body)
