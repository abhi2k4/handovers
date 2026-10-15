"""Background jobs: a small queue kept in FalkorDB, and the worker that runs it.

A job is a `:Job` node (`kind`, `run_at`, `status` queued/running/done/failed/cancelled,
`attempts`, `payload`). Keeping the queue in the graph means it survives restarts, shows up in
Graph X-ray, and needs no second store. The worker (started with the app, `JOBS_ENABLED`) wakes
every `JOBS_POLL_SECONDS`, claims what is due, runs it, and retries a failure up to three times
with a growing delay. Recurring jobs queue their next run when they finish.

Kinds:
- `digest`: the daily summary to HR, at the policy's digest hour (recurring).
- `lastday`: last day within a week and the handover not ready, to HR and the approver (daily).
- `release_held`: alerts held over quiet hours, sent once the hours end (hourly).
- `depart`: on a leaver's last day, mark them departed and end their access (one per handover).
- `letter`: send the relieving letter HR scheduled for the last day (one per handover).
"""

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from core.clock import now_ms
from core.graph import Graph
from core.logging import get_logger

log = get_logger(__name__)

MAX_ATTEMPTS = 3
RETRY_MS = 5 * 60 * 1000
HOUR_MS = 3_600_000

Handler = Callable[[Graph, dict[str, Any]], Awaitable[dict[str, Any]]]


def _id() -> str:
    return f"job:{uuid.uuid4().hex[:10]}"


def retry_at(now: int, attempts: int) -> int | None:
    """When to try a failed job again (5, then 10 minutes), or None to give up. Pure."""
    return now + RETRY_MS * attempts if attempts < MAX_ATTEMPTS else None


async def enqueue(
    graph: Graph,
    kind: str,
    run_at: int,
    key: str,
    payload: dict[str, Any] | None = None,
    handover: str | None = None,
) -> dict[str, Any]:
    rows = await graph.run(
        "job_enqueue",
        {
            "id": _id(),
            "key": key,
            "kind": kind,
            "run_at": run_at,
            "payload": json.dumps(payload or {}),
            "handover": handover or "",
            "now": now_ms(),
        },
    )
    return rows[0] if rows else {}


# ---- handlers ------------------------------------------------------------------------------------


async def _digest(graph: Graph, job: dict[str, Any]) -> dict[str, Any]:
    from services import notices

    return {"sent": len(await notices.send_digest(graph))}


async def _lastday(graph: Graph, job: dict[str, Any]) -> dict[str, Any]:
    from services import notices

    return {"sent": len(await notices.lastday_alerts(graph))}


async def _release_held(graph: Graph, job: dict[str, Any]) -> dict[str, Any]:
    from services import notices

    return await notices.release_held(graph)


async def _depart(graph: Graph, job: dict[str, Any]) -> dict[str, Any]:
    from services import handover

    return await handover.depart(graph, job["handover"])


async def _letter(graph: Graph, job: dict[str, Any]) -> dict[str, Any]:
    from services import letters

    payload = json.loads(job.get("payload") or "{}")
    return await letters.send(graph, job["handover"], payload.get("by", "HR"), payload)


HANDLERS: dict[str, Handler] = {
    "digest": _digest,
    "lastday": _lastday,
    "release_held": _release_held,
    "depart": _depart,
    "letter": _letter,
}


async def schedule_recurring(graph: Graph, kind: str, after: int) -> None:
    """Queue the next run of a recurring job, after `after`."""
    from services import org_policy

    p = await org_policy.load(graph)
    if kind == "digest" or kind == "lastday":
        at = org_policy.next_local_hour(p, after, int(p["digest_hour"]))
    elif kind == "release_held":
        at = after - after % HOUR_MS + HOUR_MS
    else:
        return
    await enqueue(graph, kind, at, f"{kind}:{at}")


RECURRING = ("digest", "lastday", "release_held")


async def ensure_recurring(graph: Graph) -> None:
    """At startup: make sure each recurring job has a next run, and every live handover has its
    departure job on its last day."""
    queued = {(j["kind"], j["status"]) for j in await graph.read("job_list", {"limit": 500})}
    now = now_ms()
    for kind in RECURRING:
        if (kind, "queued") not in queued:
            await schedule_recurring(graph, kind, now)
    for h in await graph.read("handover_list", {}):
        if h["status"] != "cancelled":
            await enqueue(graph, "depart", h["effective_at"], f"depart:{h['id']}", handover=h["id"])


async def run_due(graph: Graph, limit: int = 20) -> list[dict[str, Any]]:
    """Claim and run every due job once. Returns what ran (for the API and tests)."""
    now = now_ms()
    ran = []
    for job in await graph.run("job_claim", {"now": now, "limit": limit}):
        handler = HANDLERS.get(job["kind"])
        try:
            if handler is None:
                raise ValueError(f"unknown job kind {job['kind']}")
            result = await handler(graph, job)
            await graph.run(
                "job_finish",
                {
                    "id": job["id"],
                    "status": "done",
                    "now": now_ms(),
                    "result": json.dumps(result),
                    "error": None,
                    "retry_at": None,
                },
            )
            ran.append({**job, "status": "done", "result": result})
        except Exception as exc:  # a failed job never stops the worker
            again = retry_at(now_ms(), int(job.get("attempts") or 1))
            await graph.run(
                "job_finish",
                {
                    "id": job["id"],
                    "status": "queued" if again else "failed",
                    "now": now_ms(),
                    "result": None,
                    "error": str(exc)[:500],
                    "retry_at": again,
                },
            )
            log.warning("job_failed", job=job["id"], kind=job["kind"], error=str(exc))
            ran.append({**job, "status": "queued" if again else "failed", "error": str(exc)})
            continue
        if job["kind"] in RECURRING:
            # Next run after the one just due, so a pinned demo clock does not loop on the same slot.
            await schedule_recurring(graph, job["kind"], max(now, int(job["run_at"])) + 60_000)
    return ran


async def worker(graph: Graph, poll_seconds: float) -> None:
    """Run due jobs forever (cancelled on shutdown)."""
    try:
        await ensure_recurring(graph)
    except Exception as exc:
        log.warning("jobs_not_ready", error=str(exc))
    while True:
        try:
            await run_due(graph)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.warning("jobs_loop_error", error=str(exc))
        await asyncio.sleep(poll_seconds)


def describe(job: dict[str, Any]) -> str:
    """One line for the jobs list."""
    labels = {
        "digest": "Daily summary to HR",
        "lastday": "Last-day warnings",
        "release_held": "Send alerts held over quiet hours",
        "depart": "Last day: mark as left, end access",
        "letter": "Send the relieving letter",
    }
    return labels.get(job.get("kind") or "", job.get("kind") or "Job")
