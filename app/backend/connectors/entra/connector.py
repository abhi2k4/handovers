"""Microsoft Entra ID: the user directory. Employees, titles, departments and managers.

Microsoft Graph with an app registration (application permission User.Read.All, admin consent) and
the client-credentials flow. A full read each sync: directories are small, and a disabled account
marks the person as departed. The same values sign people in with Microsoft (identity/microsoft_entra), so they are entered once.
"""

from typing import Any

import httpx

from connectors.base import Connector, ConnectorError, Field, Person, Pull, secret
from connectors.http import get_json, post_json
from core.config import Settings
from ingestion.pipeline import Resolver

GRAPH = "https://graph.microsoft.com/v1.0"
SELECT = "displayName,mail,userPrincipalName,jobTitle,department,accountEnabled"


async def _graph_headers(http: httpx.AsyncClient, s: Settings) -> dict[str, str]:
    """An app-only Microsoft Graph token (client credentials)."""
    token = await post_json(
        http,
        f"https://login.microsoftonline.com/{s.entra_tenant_id}/oauth2/v2.0/token",
        data={
            "client_id": s.entra_client_id,
            "client_secret": secret(s.entra_client_secret),
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        },
    )
    return {"Authorization": f"Bearer {token['access_token']}"}


class Entra(Connector):
    id = "entra"
    name = "Microsoft Entra ID"
    category = "directory"
    fields = (
        Field("entra_tenant_id", "Directory (tenant) ID", placeholder="00000000-0000-0000-0000-000000000000"),
        Field("entra_client_id", "Application (client) ID", placeholder="00000000-0000-0000-0000-000000000000"),
        Field("entra_client_secret", "Client secret", secret=True,
              hint="Graph application permission User.Read.All, with admin consent. The same app signs "
                   "people in with Microsoft: add the redirect URI shown under Sign-in."),
    )  # fmt: skip

    async def check(self, http: httpx.AsyncClient, s: Settings) -> str:
        headers = await _graph_headers(http, s)
        try:
            await get_json(
                http, f"{GRAPH}/users", headers=headers, params={"$top": 1, "$select": "id"}
            )
        except ConnectorError as exc:
            raise ConnectorError(
                "Signed in, but can't read users: grant the application permission "
                "User.Read.All with admin consent."
            ) from exc
        return "Connected. Can read the directory."

    async def pull(
        self, http: httpx.AsyncClient, s: Settings, res: Resolver, since: str | None
    ) -> Pull:
        headers = await _graph_headers(http, s)
        out = Pull(cursor=since)
        url: str | None = f"{GRAPH}/users"
        params: dict[str, Any] | None = {
            "$select": SELECT,
            "$expand": "manager($select=mail,userPrincipalName)",
            "$top": 100,
        }
        while url:
            page = await get_json(http, url, headers=headers, params=params)
            for u in page.get("value", []):
                email = u.get("mail") or u.get("userPrincipalName")
                if not email or "#EXT#" in email:  # guests are not employees
                    continue
                manager = u.get("manager") or {}
                out.people.append(
                    Person(
                        email=email,
                        name=u.get("displayName") or email,
                        title=u.get("jobTitle"),
                        department=u.get("department"),
                        manager_email=manager.get("mail") or manager.get("userPrincipalName"),
                        status="active" if u.get("accountEnabled", True) else "departed",
                    )
                )
            url, params = page.get("@odata.nextLink"), None
        return out
