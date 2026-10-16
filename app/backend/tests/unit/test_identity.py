"""Sign-in providers: what each becomes in Keycloak, and how a provider is created or replaced."""

import json
from collections.abc import Callable

import httpx
import pytest
from pydantic import SecretStr

from core import keycloak
from core.config import Settings
from identity import REGISTRY
from services import identity

ENTRA = {
    "entra_tenant_id": "tenant-1",
    "entra_client_id": "client-1",
    "entra_client_secret": "s3cret",
}


def test_microsoft_signs_in_through_the_one_tenant_only() -> None:
    p = REGISTRY["microsoft"]
    provider_id, config = p.keycloak(ENTRA)
    # A generic OIDC provider pinned to the tenant, not Keycloak's multi-tenant "microsoft".
    assert provider_id == "oidc"
    assert config["issuer"] == "https://login.microsoftonline.com/tenant-1/v2.0"
    assert config["authorizationUrl"].startswith("https://login.microsoftonline.com/tenant-1/")
    assert config["clientId"] == "client-1" and config["clientSecret"] == "s3cret"
    assert p.connector == "entra"  # entered once, on the Entra connector


def test_google_signs_in_through_the_one_workspace_domain_only() -> None:
    p = REGISTRY["google"]
    provider_id, config = p.keycloak(
        {"google_domain": "example.com", "google_client_id": "g-1", "google_client_secret": "s"}
    )
    assert provider_id == "google" and config["hostedDomain"] == "example.com"
    assert config["clientId"] == "g-1" and config["clientSecret"] == "s"
    assert p.connector == "google_workspace"


def test_a_blank_secret_is_left_out_so_keycloak_keeps_its_own() -> None:
    _, config = REGISTRY["google"].keycloak(
        {"google_domain": "example.com", "google_client_id": "g-1", "google_client_secret": ""}
    )
    assert "clientSecret" not in config
    _, config = REGISTRY["microsoft"].keycloak({**ENTRA, "entra_client_secret": ""})
    assert "clientSecret" not in config


async def test_changing_a_providers_type_replaces_it() -> None:
    """The built-in "microsoft" provider becomes a tenant-pinned OIDC one: delete, then create."""
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path.endswith("/identity-provider/instances") and request.method == "GET":
            return httpx.Response(200, json=[{"alias": "microsoft", "providerId": "microsoft"}])
        if request.method == "POST":
            body = json.loads(request.content)
            assert body["providerId"] == "oidc" and body["config"]["clientId"] == "client-1"
        return httpx.Response(204)

    s = Settings(keycloak_url="http://kc")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        admin = keycloak.Admin(s, http)
        await admin.upsert_provider(
            "microsoft", "Microsoft", *REGISTRY["microsoft"].keycloak(ENTRA)
        )
    methods = [m for m, path in calls if "identity-provider" in path]
    assert methods == ["GET", "DELETE", "POST"]


# ---- one active sign-in provider -----------------------------------------------------------


class FakeKeycloak:
    """The realm's identity-provider instances, behind the admin API."""

    def __init__(self, enabled: dict[str, bool]) -> None:
        self.instances: dict[str, dict[str, object]] = {
            alias: {"alias": alias, "providerId": "oidc" if alias == "microsoft" else "google",
                    "enabled": on, "config": {}}
            for alias, on in enabled.items()
        }  # fmt: skip
        self.calls: list[tuple[str, str]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "t"})
        self.calls.append((request.method, path.rsplit("/", 1)[-1]))
        if request.method == "GET":
            return httpx.Response(200, json=list(self.instances.values()))
        if request.method in ("PUT", "POST"):
            body = json.loads(request.content)
            self.instances[body["alias"]] = body
        if request.method == "DELETE":
            self.instances.pop(path.rsplit("/", 1)[-1], None)
        return httpx.Response(204)

    def on(self) -> set[str]:
        return {a for a, rep in self.instances.items() if rep.get("enabled")}


class NoStoredConfig:
    """A graph with no values entered in the app: the directory cards come from Settings."""

    async def one(self, name: str, params: dict[str, object] | None = None) -> None:
        return None


BOTH = Settings(
    keycloak_url="http://kc",
    entra_tenant_id="tenant-1",
    entra_client_id="client-1",
    entra_client_secret=SecretStr("s"),
    google_domain="example.com",
    google_admin_email="admin@example.com",
    google_service_account_key=SecretStr("{}"),
    google_client_id="g-1",
    google_client_secret=SecretStr("gs"),
)


@pytest.fixture
def keycloak_fake(monkeypatch: pytest.MonkeyPatch) -> Callable[[dict[str, bool]], FakeKeycloak]:
    def make(enabled: dict[str, bool]) -> FakeKeycloak:
        fake = FakeKeycloak(enabled)
        real = httpx.AsyncClient
        monkeypatch.setattr(
            identity.httpx,
            "AsyncClient",
            lambda **kw: real(transport=httpx.MockTransport(fake), **kw),
        )
        return fake

    return make


async def test_making_one_provider_active_turns_the_other_off(
    keycloak_fake: Callable[[dict[str, bool]], FakeKeycloak],
) -> None:
    kc = keycloak_fake({"microsoft": True})
    turned_off = await identity.enable(NoStoredConfig(), BOTH, "google")  # type: ignore[arg-type]
    assert turned_off == ["microsoft"]
    assert kc.on() == {"google"}
    # Turned off, not deleted: Keycloak keeps its settings and people's links.
    assert "microsoft" in kc.instances and ("DELETE", "microsoft") not in kc.calls


async def test_saving_a_directory_card_never_turns_on_a_second_provider(
    keycloak_fake: Callable[[dict[str, bool]], FakeKeycloak],
) -> None:
    kc = keycloak_fake({"microsoft": True})
    assert await identity.enable_from_connector(NoStoredConfig(), BOTH, "google_workspace") == []  # type: ignore[arg-type]
    assert kc.on() == {"microsoft"}
    # The active one's own card refreshes it.
    assert await identity.enable_from_connector(NoStoredConfig(), BOTH, "entra") == ["microsoft"]  # type: ignore[arg-type]


async def test_the_first_provider_connected_becomes_active(
    keycloak_fake: Callable[[dict[str, bool]], FakeKeycloak],
) -> None:
    kc = keycloak_fake({})
    assert await identity.enable_from_connector(NoStoredConfig(), BOTH, "google_workspace") == [
        "google"
    ]  # type: ignore[arg-type]
    assert kc.on() == {"google"}


async def test_turning_off_keeps_the_provider_and_a_card_must_be_connected_first(
    keycloak_fake: Callable[[dict[str, bool]], FakeKeycloak],
) -> None:
    kc = keycloak_fake({"microsoft": True})
    await identity.disable(BOTH, "microsoft")
    assert kc.on() == set() and "microsoft" in kc.instances
    with pytest.raises(identity.InvalidValues, match="Directory"):
        await identity.enable(NoStoredConfig(), Settings(keycloak_url="http://kc"), "google")  # type: ignore[arg-type]
