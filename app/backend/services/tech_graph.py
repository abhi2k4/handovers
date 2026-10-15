"""The project graph: how Handovers itself is built, stored in FalkorDB and shown in the app.

`graph/project/architecture.json` describes the components (frontend, API routers, services,
stores, connectors, external systems) and how they link. At startup it is loaded into its own
FalkorDB graph, `handovers_project`, next to the tenant graphs: one per tenant is
`handovers__<tenant>`, so this name can never collide with one. The "How it's built" button reads
it back with a named, read-only query, so the architecture view runs on the same database and the
same query catalogue as the product.

The graph is rebuilt only when the file changes: a version (the file's hash) is stored on a
`ProjectMeta` node and compared at startup.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

from core.graph import Graph

PROJECT_GRAPH = "handovers_project"


def architecture_path(graph_dir: Path) -> Path:
    return graph_dir / "project" / "architecture.json"


def load_architecture(path: Path) -> tuple[dict[str, Any], str]:
    """The architecture file and its version (a short hash of its bytes)."""
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()[:16]


def validate(architecture: dict[str, Any]) -> list[str]:
    """Problems that would make a broken graph: duplicate ids, links to unknown components."""
    ids = [c["id"] for c in architecture["components"]]
    problems = [
        f"duplicate component id {i!r}" for i in sorted({i for i in ids if ids.count(i) > 1})
    ]
    known = set(ids)
    problems += [
        f"link {a!r} -> {b!r} names an unknown component"
        for a, b, _ in architecture["links"]
        if a not in known or b not in known
    ]
    return problems


async def ensure(graph: Graph, path: Path) -> bool:
    """Load the architecture into the project graph unless it is already current.

    Returns True when it (re)loaded. Raises ValueError for an invalid architecture file.
    """
    architecture, version = load_architecture(path)
    problems = validate(architecture)
    if problems:
        raise ValueError("graph/project/architecture.json: " + "; ".join(problems))
    current = await graph.one("project_version")
    if current and current.get("version") == version:
        return False
    await graph.run("project_clear")
    await graph.run(
        "project_load",
        {
            "components": architecture["components"],
            "links": [{"from": a, "to": b, "how": how} for a, b, how in architecture["links"]],
            "version": version,
        },
    )
    return True


async def read(graph: Graph) -> dict[str, Any]:
    """Components and links for the view, plus the Cypher that read them."""
    row = await graph.one("project_graph")
    return {
        "graph": PROJECT_GRAPH,
        "nodes": (row or {}).get("nodes") or [],
        "links": [link for link in (row or {}).get("links") or [] if link.get("source")],
        "cypher": graph.catalog.source("project_graph"),
    }
