"""The project graph round-trips through FalkorDB: loaded once, read back, reloaded on change."""

import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio

from core.config import Settings
from core.falkordb import FalkorDBClient
from core.graph import Graph, QueryCatalog
from services import tech_graph

pytestmark = pytest.mark.integration

GRAPH = "itest_handovers_project"  # never the real project graph


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def graph() -> AsyncIterator[Graph]:
    settings = Settings()
    client = FalkorDBClient(settings)
    if not (await client.status()).ok:
        await client.close()
        pytest.skip("FalkorDB not reachable")
    if await client.graph_exists(GRAPH):
        await client.graph(GRAPH).delete()
    yield Graph(client, QueryCatalog(settings.graph_dir), graph_name=GRAPH)
    if await client.graph_exists(GRAPH):
        await client.graph(GRAPH).delete()
    await client.close()


@pytest.mark.asyncio(loop_scope="module")
async def test_the_architecture_loads_once_and_reads_back(graph: Graph) -> None:
    path = tech_graph.architecture_path(Settings().graph_dir)
    architecture, _ = tech_graph.load_architecture(path)

    assert await tech_graph.ensure(graph, path) is True
    assert await tech_graph.ensure(graph, path) is False  # same file: nothing reloaded

    view = await tech_graph.read(graph)
    assert {n["id"] for n in view["nodes"]} == {c["id"] for c in architecture["components"]}
    assert len(view["links"]) == len(architecture["links"])
    assert "MATCH (c:Component)" in view["cypher"]  # the named query, shown to the viewer


@pytest.mark.asyncio(loop_scope="module")
async def test_a_changed_file_replaces_the_graph(graph: Graph, tmp_path: Path) -> None:
    small = {
        "components": [
            {"id": "a", "name": "A", "kind": "api", "summary": "", "path": ""},
            {"id": "b", "name": "B", "kind": "store", "summary": "", "path": ""},
        ],
        "links": [["a", "b", "uses"]],
    }
    path = tmp_path / "architecture.json"
    path.write_text(json.dumps(small), encoding="utf-8")

    assert await tech_graph.ensure(graph, path) is True
    view = await tech_graph.read(graph)
    assert {n["id"] for n in view["nodes"]} == {"a", "b"}
    assert view["links"] == [{"source": "a", "target": "b", "how": "uses"}]
