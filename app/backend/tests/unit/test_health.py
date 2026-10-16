from fastapi.testclient import TestClient

from core.config import Settings
from core.falkordb import FalkorDBStatus, _graph_module_version
from main import create_app


class FakeFalkorDB:
    def __init__(self, status: FalkorDBStatus) -> None:
        self._status = status
        self.closed = False

    @property
    def graph_name(self) -> str:
        return "handovers__test"

    async def status(self) -> FalkorDBStatus:
        return self._status

    async def graph_exists(self, name: str | None = None) -> bool:
        return False  # an empty tenant: startup logs how to load the sample company

    async def close(self) -> None:
        self.closed = True


def _client(db_status: FalkorDBStatus) -> TestClient:
    # Pinned, so a developer's .env (seeding, sign-in) cannot change what this test runs.
    settings = Settings(handovers_tenant="test", seed_on_start=False, keycloak_url="")
    app = create_app(settings, falkordb=FakeFalkorDB(db_status))  # type: ignore[arg-type]
    return TestClient(app)


def test_healthz_is_ok_without_database() -> None:
    with _client(FalkorDBStatus(ok=False, error="down")) as client:
        assert client.get("/healthz").json() == {"status": "ok"}


def test_readyz_reports_falkordb_up() -> None:
    with _client(FalkorDBStatus(ok=True, module_version=60001)) as client:
        response = client.get("/readyz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["falkordb"] == {
        "ok": True,
        "graph": "handovers__test",
        "module_version": 60001,
        "error": None,
    }


def test_readyz_is_503_when_falkordb_down() -> None:
    with _client(FalkorDBStatus(ok=False, error="ConnectionError: refused")) as client:
        response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


def test_api_status_is_200_even_when_degraded() -> None:
    with _client(FalkorDBStatus(ok=False, error="down")) as client:
        response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json()["falkordb"]["ok"] is False


def test_tenant_graph_name() -> None:
    assert Settings(handovers_tenant="northwind").tenant_graph == "handovers__northwind"


def test_graph_module_version_parsing() -> None:
    reply = [
        ["name", "graph", "ver", 60001, "path", "/x/falkordb.so", "args", []],
        ["name", "vectorset", "ver", 1, "path", "", "args", []],
    ]
    assert _graph_module_version(reply) == 60001
    assert _graph_module_version([]) is None
