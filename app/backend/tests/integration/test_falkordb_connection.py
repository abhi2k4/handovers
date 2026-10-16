"""Integration tests against the real FalkorDB from deployment/docker-compose.yml.

Run with FalkorDB up:  uv run pytest -m integration
Skipped automatically when FalkorDB is not reachable.
"""

from collections.abc import AsyncIterator

import pytest

from core.config import Settings
from core.falkordb import FalkorDBClient

pytestmark = pytest.mark.integration


@pytest.fixture
async def client() -> AsyncIterator[FalkorDBClient]:
    db = FalkorDBClient(Settings(handovers_tenant="itest"))
    if not (await db.status()).ok:
        await db.close()
        pytest.skip("FalkorDB not reachable; start it with the dev compose command")
    yield db
    if await db.graph_exists():
        await db.graph().delete()
    await db.close()


async def test_status_reports_graph_module(client: FalkorDBClient) -> None:
    status = await client.status()
    assert status.ok
    assert status.module_version is not None


async def test_parameterised_round_trip(client: FalkorDBClient) -> None:
    graph = client.graph()
    await graph.query("CREATE (:Probe {id: $id, n: $n})", {"id": "probe:1", "n": 42})
    result = await graph.ro_query("MATCH (p:Probe {id: $id}) RETURN p.n", {"id": "probe:1"})
    assert result.result_set == [[42]]
