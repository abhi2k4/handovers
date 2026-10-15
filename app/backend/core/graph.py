"""Named, parameterised Cypher queries over the tenant graph.

Every query lives in `graph/queries/<name>.cypher` and is loaded once. Code refers to queries by
name and always passes parameters; Cypher is never assembled from user input. The only template
substitution allowed is `{label}`, filled from a closed whitelist (see `KNOWLEDGE_LABELS`).
"""

import time
from pathlib import Path
from typing import Any

from falkordb.edge import Edge
from falkordb.node import Node
from falkordb.path import Path as GraphPath
from redis.exceptions import ResponseError

from core import trace
from core.falkordb import FalkorDBClient

KNOWLEDGE_LABELS = frozenset({"Decision", "Procedure", "Claim"})
SOURCE_LABELS = frozenset(
    {
        "EOD",
        "Message",
        "Ticket",
        "PullRequest",
        "Commit",
        "Meeting",
        "Document",
        "Upload",
        "CRMNote",
        "InterviewAnswer",
    }
)


class QueryCatalog:
    """Loads `graph/queries/*.cypher` into memory, keyed by file stem."""

    def __init__(self, graph_dir: Path) -> None:
        self._dir = graph_dir / "queries"
        self._queries: dict[str, str] = {}
        for path in sorted(self._dir.glob("*.cypher")):
            self._queries[path.stem] = _strip_comments(path.read_text(encoding="utf-8"))

    def get(self, name: str, label: str | None = None) -> str:
        text = self._queries[name]
        if "{label}" in text:
            if label not in KNOWLEDGE_LABELS | SOURCE_LABELS:
                raise ValueError(f"label {label!r} is not whitelisted for query {name}")
            text = text.replace("{label}", label)
        return text

    def source(self, name: str) -> str:
        """Raw query text (for the transparency endpoint)."""
        return self._queries[name]

    def names(self) -> list[str]:
        return sorted(self._queries)


def _strip_comments(text: str) -> str:
    lines = [line for line in text.splitlines() if not line.strip().startswith("//")]
    return "\n".join(lines).strip()


def _plain(value: Any) -> Any:
    if isinstance(value, Node):
        return {**value.properties, "_labels": list(value.labels)}
    if isinstance(value, Edge):
        return {**value.properties, "_type": value.relation}
    if isinstance(value, GraphPath):
        return {
            "nodes": [_plain(n) for n in value.nodes()],
            "edges": [_plain(e) for e in value.edges()],
        }
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


class Graph:
    """Runs catalogued queries against the tenant graph (or another named graph) as dicts."""

    def __init__(
        self, client: FalkorDBClient, catalog: QueryCatalog, graph_name: str | None = None
    ) -> None:
        self._client = client
        self.catalog = catalog
        # None: the tenant graph. Set only for the project graph (services/tech_graph.py).
        self._graph_name = graph_name

    async def run(
        self, name: str, params: dict[str, Any] | None = None, *, label: str | None = None
    ) -> list[dict[str, Any]]:
        """Read-write query."""
        started = time.perf_counter()
        result = await self._client.graph(self._graph_name).query(
            self.catalog.get(name, label), params or {}
        )
        rows = _rows(result)
        trace.record(
            name, label, params or {}, len(rows), (time.perf_counter() - started) * 1000, "write"
        )
        return rows

    async def read(
        self, name: str, params: dict[str, Any] | None = None, *, label: str | None = None
    ) -> list[dict[str, Any]]:
        """Read-only query (GRAPH.RO_QUERY): the server rejects writes."""
        started = time.perf_counter()
        try:
            result = await self._client.graph(self._graph_name).ro_query(
                self.catalog.get(name, label), params or {}
            )
        except ResponseError as exc:
            # The tenant graph does not exist yet (nothing seeded or ingested): an empty company,
            # not a server error. The startup log says how to load the sample data.
            if "empty key" in str(exc):
                return []
            raise
        rows = _rows(result)
        trace.record(
            name, label, params or {}, len(rows), (time.perf_counter() - started) * 1000, "read"
        )
        return rows

    async def one(self, name: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        rows = await self.read(name, params)
        return rows[0] if rows else None

    async def raw(self, cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Schema bootstrap only (index DDL). Never call with user input."""
        result = await self._client.graph(self._graph_name).query(cypher, params or {})
        return _rows(result)


def _rows(result: Any) -> list[dict[str, Any]]:
    header = [col[1] if isinstance(col, (list, tuple)) else col for col in (result.header or [])]
    return [dict(zip(header, (_plain(v) for v in row), strict=False)) for row in result.result_set]
