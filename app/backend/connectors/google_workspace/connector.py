"""Google Workspace: the user directory. Employees, titles, departments and managers.

The Admin SDK Directory API (users.list) with a service account that has domain-wide delegation
for the read-only scope below, acting as a Workspace admin (Google requires an admin subject for
directory reads). A full read each sync: directories are small, and a suspended or archived account
marks the person as departed. The same Workspace signs people in with Google, pinned to its domain
(identity/google_workspace), with an OAuth client entered on the same card.
https://developers.google.com/workspace/admin/directory/reference/rest/v1/users/list
"""

import json
import time
from typing import Any

import httpx
import jwt

from connectors.base import Connector, ConnectorError, Field, Person, Pull, secret
from connectors.http import get_json, post_json
from core.config import Settings
from ingestion.pipeline import Resolver

DIRECTORY = "https://admin.googleapis.com/admin/directory/v1"
SCOPE = "https://www.googleapis.com/auth/admin.directory.user.readonly"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def _service_account(s: Settings) -> dict[str, str]:
    try:
        key = json.loads(secret(s.google_service_account_key))
    except json.JSONDecodeError as exc:
        raise ConnectorError("The service account key is not valid JSON") from exc
    if not isinstance(key, dict) or not key.get("client_email") or not key.get("private_key"):
        raise ConnectorError("The service account key has no client_email or private_key")
    return key


async def _headers(http: httpx.AsyncClient, s: Settings) -> dict[str, str]:
    """An access token for the service account acting as the admin (JWT bearer grant)."""
    key = _service_account(s)
    now = int(time.time())
    claims = {
        "iss": key["client_email"],
        "sub": s.google_admin_email,
        "scope": SCOPE,
        "aud": TOKEN_URL,
        "iat": now,
        "exp": now + 3600,
    }
    try:
        assertion = jwt.encode(claims, key["private_key"], algorithm="RS256")
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise ConnectorError("The service account's private key could not be read") from exc
    token = await post_json(
        http,
        TOKEN_URL,
        data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
    )
    return {"Authorization": f"Bearer {token['access_token']}"}


def _person(u: dict[str, Any]) -> Person | None:
    email = u.get("primaryEmail")
    if not email:
        return None
    orgs = u.get("organizations") or []
    org = next((o for o in orgs if o.get("primary")), orgs[0] if orgs else {})
    manager = next(
        (r.get("value") for r in u.get("relations") or [] if r.get("type") == "manager"), None
    )
    return Person(
        email=email,
        name=(u.get("name") or {}).get("fullName") or email,
        title=org.get("title"),
        department=org.get("department"),
        manager_email=manager,
        status="departed" if u.get("suspended") or u.get("archived") else "active",
    )


class GoogleWorkspace(Connector):
    id = "google_workspace"
    name = "Google Workspace"
    category = "directory"
    fields = (
        Field("google_domain", "Workspace domain", placeholder="example.com",
              hint="Only accounts in this domain are read and can sign in."),
        Field("google_admin_email", "Admin to act as", placeholder="admin@example.com",
              hint="A Workspace admin; directory reads are made on their behalf."),
        Field("google_service_account_key", "Service account key (JSON)", secret=True,
              placeholder='{"type": "service_account", ...}',
              hint="Domain-wide delegation for admin.directory.user.readonly (Admin console > "
                   "Security > API controls)."),
        Field("google_client_id", "OAuth client ID", placeholder="1234567890-abc.apps.googleusercontent.com",
              hint="For sign-in: a Web application OAuth client with the redirect URI shown under Sign-in."),
        Field("google_client_secret", "OAuth client secret", secret=True),
    )  # fmt: skip

    async def check(self, http: httpx.AsyncClient, s: Settings) -> str:
        headers = await _headers(http, s)
        try:
            await get_json(
                http,
                f"{DIRECTORY}/users",
                headers=headers,
                params={"domain": s.google_domain, "maxResults": 1, "fields": "users(id)"},
            )
        except ConnectorError as exc:
            raise ConnectorError(
                f"Got a token, but can't read the {s.google_domain} directory: check the "
                "domain-wide delegation scope and that the admin email is an admin."
            ) from exc
        return f"Connected. Can read the {s.google_domain} directory."

    async def pull(
        self, http: httpx.AsyncClient, s: Settings, res: Resolver, since: str | None
    ) -> Pull:
        headers = await _headers(http, s)
        out = Pull(cursor=since)
        params: dict[str, Any] = {"domain": s.google_domain, "maxResults": 500}
        while True:
            page = await get_json(http, f"{DIRECTORY}/users", headers=headers, params=params)
            out.people += [p for p in map(_person, page.get("users", [])) if p]
            if not page.get("nextPageToken"):
                return out
            params["pageToken"] = page["nextPageToken"]
