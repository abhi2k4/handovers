"""Bootstrap the tenant graph (indexes) and load the Northwind fixtures.

Fixtures carry their extraction results, so loading is deterministic and needs no LLM. Live uploads
run the same writer after extraction (see ingestion/pipeline.py).

Run:  uv run python -m seed.load            (bootstrap + load into an empty graph)
      uv run python -m seed.load --reset    (delete the tenant graph first)
"""

import argparse
import asyncio
import json
import time

from core.config import get_settings
from core.falkordb import FalkorDBClient
from core.graph import Graph, QueryCatalog
from ingestion.schema import Org, SourceIn
from ingestion.writer import WriteStats, recompute_confidence, write_org, write_source


async def bootstrap(graph: Graph) -> int:
    """Create indexes. Idempotent: 'already indexed' errors are ignored."""
    path = get_settings().graph_dir / "schema" / "indexes.cypher"
    created = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        stmt = line.strip()
        if not stmt or stmt.startswith("//"):
            continue
        try:
            await graph.raw(stmt)
            created += 1
        except Exception as exc:
            if "already indexed" not in str(exc).lower():
                raise
    return created


async def open_scenario(graph: Graph) -> None:
    """Demo state: Nisha resigned eight days ago and her handover is in flight (22 days left)."""
    from core.clock import DAY_MS, now_ms
    from services import handover

    hid = await handover.open_handover(graph, "emp:nisha", "emp:ananya", 22)
    started = now_ms() - 8 * DAY_MS
    await graph.raw(
        "MATCH (h:Handover {id: $id}) SET h.created_at = $started, h.notice_days = 30",
        {"id": hid, "started": started},
    )


async def load(graph: Graph, *, dataset: str = "northwind") -> WriteStats:
    base = get_settings().graph_dir / "seed" / dataset
    org = Org.model_validate_json((base / "org.json").read_text(encoding="utf-8"))
    await write_org(graph, org)
    stats = WriteStats()
    with (base / "sources.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                await write_source(
                    graph, SourceIn.model_validate(json.loads(line)), origin="seed", stats=stats
                )
    await recompute_confidence(graph)
    return stats


async def main(reset: bool, scenario: bool) -> None:
    settings = get_settings()
    client = FalkorDBClient(settings)
    graph = Graph(client, QueryCatalog(settings.graph_dir))
    try:
        if reset and await client.graph_exists():
            await client.graph().delete()
            print(f"deleted graph {client.graph_name}")
        started = time.perf_counter()
        created = await bootstrap(graph)
        stats = await load(graph)
        if scenario:
            await open_scenario(graph)
        took = time.perf_counter() - started
        print(
            f"indexes: {created} new · sources: {stats.sources} · facts: {stats.facts} {stats.by_kind} · {took:.1f}s"
        )
        for row in await graph.read("graph_stats"):
            print(f"  {row['label']:<16} {row['n']}")
    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    parser.add_argument(
        "--no-scenario", action="store_true", help="skip the in-flight demo handover"
    )
    args = parser.parse_args()
    asyncio.run(main(args.reset, not args.no_scenario))
