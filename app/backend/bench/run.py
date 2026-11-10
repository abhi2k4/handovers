"""Benchmark: can the successor answer, from the right source, without leaking private data?

Deterministic and LLM-free (retrieval level). Runs on its own tenant graph so the demo is untouched.

Setups compared on the same questions (graph/seed/northwind/benchmark.json):
  before     successor's memory before the handover (should know nothing)
  handovers  successor after the approved handover: graph-scoped retrieval over inherited memory
  flat       full-text search over every document in the company, no graph scoping
  naive      every memory of the leaver copied to the successor, with no review or filters

Metrics:
  answered@4   share of answerable questions whose gold item is among the 4 retrieved items
  top1         share of answerable questions whose first retrieved item is gold (the current answer)
  leaks        private questions that returned the private item (must be 0)

Run:  uv run python -m bench.run          (writes graph/benchmark/results/<date>.json)
      uv run python -m bench.run --check  (CI: compares with the latest committed run, writes
                                           nothing, exits 1 on a regression or any leak)
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.config import Settings, get_settings
from core.falkordb import FalkorDBClient
from core.graph import Graph, QueryCatalog
from core.llm import LLM
from seed.load import bootstrap, load
from services import companion
from services import handover as svc

SUCCESSOR = {"emp:arjun": "emp:farhan", "emp:nisha": "emp:ananya"}
APPROVER = {"emp:arjun": "emp:priya", "emp:nisha": "emp:aditi"}


async def fresh(tenant: str) -> tuple[FalkorDBClient, Graph]:
    settings = Settings(handovers_tenant=tenant)
    client = FalkorDBClient(settings)
    if await client.graph_exists():
        await client.graph().delete()
    graph = Graph(client, QueryCatalog(settings.graph_dir))
    await bootstrap(graph)
    await load(graph)
    return client, graph


async def handover(graph: Graph, llm: LLM, leaver: str, answers: dict[str, str]) -> None:
    hid = await svc.open_handover(graph, leaver, SUCCESSOR[leaver], 30)
    h = await svc.get(graph, hid)
    for gap in svc.interview_questions(h["gaps"]):
        if gap["target_id"] in answers:
            preview = await svc.preview_answer(graph, llm, gap["id"], answers[gap["target_id"]])
            await svc.confirm_answer(graph, gap["id"], answers[gap["target_id"]], preview["facts"])
    await svc.approve_and_transfer(graph, hid, APPROVER[leaver])


def score(rows: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [r for r in rows if r["answerable"]]
    private = [r for r in rows if not r["answerable"]]
    return {
        "answered_at_4": round(sum(r["hit"] for r in answerable) / len(answerable), 3),
        "top1": round(sum(r["top1"] for r in answerable) / len(answerable), 3),
        "leaks": sum(r["hit"] for r in private),
        "answerable": len(answerable),
        "private": len(private),
    }


async def graph_setup(graph: Graph, questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for q in questions:
        ids = await companion.retrieve_ids(graph, SUCCESSOR[q["owner"]], q["question"])
        out.append(
            {
                **q,
                "retrieved": ids,
                "hit": any(i in q["gold"] for i in ids),
                "top1": bool(ids) and ids[0] in q["gold"],
            }
        )
    return out


async def flat_setup(graph: Graph, questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gold_ids = sorted({g for q in questions for g in q["gold"]})
    evidence = {
        r["id"]: set(r["sources"]) for r in await graph.read("evidence_of", {"ids": gold_ids})
    }
    out = []
    for q in questions:
        rows = await graph.read(
            "flat_search", {"q": companion.fulltext_query(q["question"]), "k": 4}
        )
        ids = [r["id"] for r in rows]
        gold_sources = set().union(*(evidence.get(g, set()) for g in q["gold"]))
        out.append(
            {
                **q,
                "retrieved": ids,
                "hit": any(i in gold_sources for i in ids),
                "top1": bool(ids) and ids[0] in gold_sources,
            }
        )
    return out


def latest_committed(results_dir: Path) -> dict[str, Any] | None:
    """The newest committed run (file names start with the date, so the last name is newest)."""
    runs = sorted(results_dir.glob("*.json"))
    if not runs:
        return None
    data: dict[str, Any] = json.loads(runs[-1].read_text(encoding="utf-8"))
    return data


def regressions(now: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    """What got worse than the committed run. Empty: no regression.

    The handover setup must answer at least as well, and leak nothing; the successor must still
    know nothing before the handover (otherwise private memory is reachable early).
    """
    out = []
    got, was = now["setups"]["handovers"], baseline["setups"]["handovers"]
    for metric in ("answered_at_4", "top1"):
        if got[metric] < was[metric]:
            out.append(f"handovers {metric}: {got[metric]:.3f} < committed {was[metric]:.3f}")
    if got["leaks"] > 0:
        out.append(f"handovers leaks: {got['leaks']} (must be 0)")
    before, before_was = now["setups"]["before"], baseline["setups"]["before"]
    if before["answered_at_4"] > before_was["answered_at_4"]:
        out.append(
            f"before answered_at_4: {before['answered_at_4']:.3f} > committed "
            f"{before_was['answered_at_4']:.3f} (the successor knows things before the handover)"
        )
    return out


async def main(check: bool = False) -> int:
    base = get_settings().graph_dir
    questions = json.loads(
        (base / "seed" / "northwind" / "benchmark.json").read_text(encoding="utf-8")
    )
    answers = json.loads(
        (base / "seed" / "northwind" / "interview.json").read_text(encoding="utf-8")
    )
    llm = LLM(Settings(llm_provider="none"))
    started = time.perf_counter()

    client, graph = await fresh("bench")
    engine = (await client.status()).module_version
    try:
        before = await graph_setup(graph, questions)
        for leaver in SUCCESSOR:
            await handover(graph, llm, leaver, answers)
        after = await graph_setup(graph, questions)
        flat = await flat_setup(graph, questions)
    finally:
        await client.graph().delete()
        await client.close()

    client, graph = await fresh("bench_naive")
    try:
        for leaver, successor in SUCCESSOR.items():
            await graph.run("naive_copy", {"from": leaver, "to": successor})
        naive = await graph_setup(graph, questions)
    finally:
        await client.graph().delete()
        await client.close()

    setups = {
        "before": score(before),
        "handovers": score(after),
        "flat": score(flat),
        "naive": score(naive),
    }
    results = {
        "run_at": datetime.now(UTC).isoformat(),
        "questions": len(questions),
        "llm": "none (retrieval only)",
        "falkordb_module_version": engine,
        "setups": setups,
        "detail": {"handovers": after, "flat": flat, "naive": naive},
        "seconds": round(time.perf_counter() - started, 2),
    }
    out = base / "benchmark" / "results"
    print(f"{'setup':<12}{'answered@4':>12}{'top1':>8}{'leaks':>8}")
    for name, s in setups.items():
        print(f"{name:<12}{s['answered_at_4']:>12.0%}{s['top1']:>8.0%}{s['leaks']:>8}")

    if check:
        baseline = latest_committed(out)
        if baseline is None:
            print("No committed run to compare with.")
            return 1
        failed = regressions(results, baseline)
        for line in failed:
            print(f"REGRESSION {line}")
        print("Benchmark check: " + ("FAILED" if failed else f"ok (vs {baseline['run_at'][:10]})"))
        return 1 if failed else 0

    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{datetime.now(UTC):%Y-%m-%d}-falkordb-{engine}.json"
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"FalkorDB {engine} | {len(questions)} questions ({setups['handovers']['private']} private) | {results['seconds']}s | {path}"
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="compare with the latest committed run; write nothing"
    )
    sys.exit(asyncio.run(main(parser.parse_args().check)))
