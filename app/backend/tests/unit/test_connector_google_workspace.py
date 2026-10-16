"""Google Workspace connector against recorded Directory API responses (no network)."""

import json
from urllib.parse import parse_qs

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import SecretStr

from connectors.base import ConnectorError
from connectors.google_workspace import GoogleWorkspace
from core.config import Settings
from ingestion.pipeline import Resolver

PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PEM = PRIVATE.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
).decode()

USERS = [
    {
        "primaryEmail": "meera@example.com",
        "name": {"fullName": "Meera Iyer"},
        "organizations": [{"title": "HR Lead", "department": "People", "primary": True}],
    },
    {
        "primaryEmail": "arjun@example.com",
        "name": {"fullName": "Arjun Mehta"},
        "organizations": [{"title": "Engineer", "department": "Payments"}],
        "relations": [{"type": "manager", "value": "meera@example.com"}],
    },
    {"primaryEmail": "left@example.com", "name": {"fullName": "Ex Employee"}, "suspended": True},
]


def settings(key: str | None = None) -> Settings:
    sa = {"type": "service_account", "client_email": "sync@proj.iam.gserviceaccount.com",
          "private_key": PEM}  # fmt: skip
    return Settings(
        google_domain="example.com",
        google_admin_email="admin@example.com",
        google_service_account_key=SecretStr(key if key is not None else json.dumps(sa)),
        google_client_id="client.apps.googleusercontent.com",
        google_client_secret=SecretStr("secret"),
    )


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.host == "oauth2.googleapis.com":
        form = parse_qs(request.content.decode())
        claims = jwt.decode(
            form["assertion"][0], PRIVATE.public_key(), algorithms=["RS256"],
            audience="https://oauth2.googleapis.com/token",
        )  # fmt: skip
        # The service account acts as the admin, read-only on users.
        assert claims["sub"] == "admin@example.com"
        assert claims["scope"].endswith("admin.directory.user.readonly")
        return httpx.Response(200, json={"access_token": "t"})
    assert request.headers["Authorization"] == "Bearer t"
    assert request.url.params["domain"] == "example.com"
    if request.url.params.get("pageToken") == "2":
        return httpx.Response(200, json={"users": USERS[2:]})
    return httpx.Response(200, json={"users": USERS[:2], "nextPageToken": "2"})


async def test_people_with_titles_managers_and_leavers_across_pages() -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        pull = await GoogleWorkspace().pull(http, settings(), Resolver([], [], []), since=None)
    people = {p.email: p for p in pull.people}
    assert set(people) == {"meera@example.com", "arjun@example.com", "left@example.com"}
    assert people["meera@example.com"].title == "HR Lead"
    assert people["arjun@example.com"].department == "Payments"
    assert people["arjun@example.com"].manager_email == "meera@example.com"
    assert people["left@example.com"].status == "departed"


async def test_check_reads_the_directory() -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        assert "example.com" in await GoogleWorkspace().check(http, settings())


async def test_a_pasted_key_that_is_not_json_says_so() -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(ConnectorError, match="not valid JSON"):
            await GoogleWorkspace().check(http, settings("not json"))


async def test_a_key_that_is_not_a_private_key_says_so() -> None:
    bad = json.dumps({"client_email": "x@y", "private_key": "not a key"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(ConnectorError, match="private key"):
            await GoogleWorkspace().check(http, settings(bad))


def test_configured_only_with_every_value() -> None:
    assert GoogleWorkspace().configured(settings())
    assert not GoogleWorkspace().configured(Settings(google_domain="example.com"))
