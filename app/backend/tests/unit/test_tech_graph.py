"""The committed architecture file is a valid graph: unique ids, no link to a missing component."""

from core.config import Settings
from services import tech_graph


def test_the_committed_architecture_is_valid() -> None:
    path = tech_graph.architecture_path(Settings().graph_dir)
    architecture, version = tech_graph.load_architecture(path)
    assert tech_graph.validate(architecture) == []
    assert len(version) == 16
    linked = {end for a, b, _ in architecture["links"] for end in (a, b)}
    # Every component is connected to something, so the view has no stray dots.
    assert {c["id"] for c in architecture["components"]} <= linked


def test_broken_links_and_duplicates_are_reported() -> None:
    broken = {
        "components": [{"id": "a"}, {"id": "a"}],
        "links": [["a", "ghost", "uses"]],
    }
    problems = tech_graph.validate(broken)
    assert "duplicate component id 'a'" in problems
    assert any("ghost" in p for p in problems)


def test_the_project_route_is_not_taken_for_a_trace_id() -> None:
    """/api/xray/project must reach the project graph, not the /{trace_id} route after it."""
    from fastapi.testclient import TestClient

    from core.falkordb import FalkorDBStatus
    from main import create_app
    from tests.unit.test_health import FakeFalkorDB

    settings = Settings(handovers_tenant="test", seed_on_start=False, keycloak_url="")
    app = create_app(settings, falkordb=FakeFalkorDB(FalkorDBStatus(ok=False, error="down")))  # type: ignore[arg-type]
    with TestClient(app) as client:
        response = client.get("/api/xray/project")
    # FalkorDB is down in this test: the project route answers 503, not "unknown trace" 404.
    assert response.status_code == 503
