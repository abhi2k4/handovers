"""HTTP helpers for connectors: JSON calls with errors an admin can read, never a credential."""

from typing import Any

import httpx

from connectors.base import ConnectorError


async def get_json(http: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
    """GET with a readable error. Status and URL path only: never headers, never the token."""
    return await request_json(http, "GET", url, **kwargs)


async def post_json(http: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
    return await request_json(http, "POST", url, **kwargs)


async def request_json(http: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> Any:
    try:
        r = await http.request(method, url, **kwargs)
    except httpx.HTTPError as exc:
        raise ConnectorError(f"Could not reach {httpx.URL(url).host}") from exc
    if r.status_code in (401, 403):
        raise ConnectorError(f"{httpx.URL(url).host} refused the credentials ({r.status_code})")
    if r.status_code >= 400:
        raise ConnectorError(
            f"{httpx.URL(url).host} returned {r.status_code} for {httpx.URL(url).path}"
        )
    return r.json()
