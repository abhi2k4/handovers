"""The landing view: what could walk out the door, and what to do about it today.

Everything is computed from graph queries and the same gap rules a handover uses, so every number
on the dashboard links to evidence.
"""

import asyncio
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from core.clock import DAY_MS, now_ms
from core.graph import Graph
from services import analysis, clearance, handover, handover_rules, ramp, readiness

HEATMAP_WEEKS = 26
SEVERITY = {"bad": 0, "warn": 1, "info": 2}


def _day(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=UTC).date().isoformat()


async def _handovers(graph: Graph, now: int) -> list[dict[str, Any]]:
    rows = await graph.read("handover_list", {})
    out = []
    for h in rows:
        if h["status"] == "cancelled":  # a withdrawn resignation is not an exit in progress
            continue
        gaps = await graph.read("gap_list", {"handover": h["id"]})
        questions, _ = handover_rules.interview_sets(gaps)
        answered = sum(1 for g in questions if g["status"] == "answered")
        artifacts = {
            a["kind"] for a in await graph.read("dash_handover_artifacts", {"handover": h["id"]})
        }
        detail = await graph.one("handover_get", {"id": h["id"]}) or {}
        plan = await ramp.get(graph, h["id"])
        # The same last-day checks as the handover page, so every screen agrees on "ready".
        ready = readiness.build(
            {**detail, "gaps": gaps},
            artifacts,
            plan["status"] if plan else None,
            now,
            pending := await handover.pending_followup(graph, {**detail, "gaps": gaps}),
            await clearance.tally(graph, h["id"]),
        )
        out.append(
            {
                **h,
                # The leaver stays until the last day even after the transfer is approved.
                "days_left": max(0, round((h["effective_at"] - now) / DAY_MS)),
                "notice_days": detail.get("notice_days"),
                "strong_candidates": sum(
                    1
                    for c in await graph.read("candidate_list", {"handover": h["id"]})
                    if c["must_total"] and c["must_met"] == c["must_total"]
                ),
                "successor_id": detail.get("successor_id"),
                "questions": len(questions),
                "answered": answered,
                "open_access": [
                    g for g in gaps if g["rule"] == "G7A" and g.get("resolution") != "reassigned"
                ],
                "ready": ready["ready"],
                "stage": ready["stage"],
                "stages": ready["stages"],
                "pending": pending,
                "steps": [
                    {"key": i["key"], "label": i["short"], "done": i["done"], "href": i["href"]}
                    for i in ready["items"]
                ],
            }
        )
    return out


async def handovers(graph: Graph, now: int) -> list[dict[str, Any]]:
    """Every handover with its readiness steps and stage (also the daily digest's source)."""
    return await _handovers(graph, now)


def _attention(
    handovers: list[dict[str, Any]], people_detail: dict[str, dict[str, Any]], review: int, now: int
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for h in handovers:
        if h["status"] == "transferred":
            if h.get("pending"):
                items.append(
                    {
                        "severity": "info",
                        "kind": "transfer",
                        "title": f"Send {h['employee'].split()[0]}'s new knowledge",
                        "detail": f"{h['pending']} captured since approval",
                        "href": f"/handovers/{h['id']}?tab=transfer",
                        "person": h["employee"],
                    }
                )
            continue
        first = h["employee"].split()[0]
        for g in h["open_access"]:
            items.append(
                {
                    "severity": "bad",
                    "kind": "access",
                    "title": g["title"],
                    "detail": f"Only {first} is admin · {h['days_left']} days left",
                    "href": "/accounts",
                    "person": h["employee"],
                }
            )
        if not h.get("successor_id"):
            items.append(
                {
                    "severity": "warn",
                    "kind": "successor",
                    "title": f"Choose a successor for {first}",
                    "detail": f"{h['days_left']} days left",
                    "href": f"/handovers/{h['id']}",
                    "person": h["employee"],
                }
            )
        remaining = h["questions"] - h["answered"]
        if remaining:
            items.append(
                {
                    "severity": "warn",
                    "kind": "interview",
                    "title": f"Exit interview with {first}",
                    "detail": f"{remaining} {'question' if remaining == 1 else 'questions'} only they can answer",
                    "href": f"/handovers/{h['id']}?tab=interview",
                    "person": h["employee"],
                }
            )
        if h.get("strong_candidates"):
            n = h["strong_candidates"]
            items.append(
                {
                    "severity": "info",
                    "kind": "candidate",
                    "title": f"{n} {'candidate has' if n == 1 else 'candidates have'} every must-have",
                    "detail": f"For {first}'s role",
                    "href": f"/handovers/{h['id']}?tab=candidates",
                    "person": h["employee"],
                }
            )
        if h["questions"] and not remaining and h["status"] != "transferred":
            items.append(
                {
                    "severity": "info",
                    "kind": "transfer",
                    "title": f"Approve {first}'s handover",
                    "detail": f"To {h.get('successor') or 'successor'}",
                    "href": f"/handovers/{h['id']}?tab=transfer",
                    "person": h["employee"],
                }
            )
    for pid, p in people_detail.items():
        for r in p.get("responsibilities", []):
            # Calendar-driven work only: a missed monthly close or key rotation is a real signal.
            if (
                r.get("overdue")
                and not r.get("co_owners")
                and r.get("cadence") in ("monthly", "quarterly")
            ):
                items.append(
                    {
                        "severity": "bad",
                        "kind": "overdue",
                        "title": r["title"],
                        "detail": f"Overdue · only {p['name'].split()[0]} does it",
                        "href": f"/people/{pid}",
                        "person": p["name"],
                    }
                )
    if review:
        items.append(
            {
                "severity": "info",
                "kind": "review",
                "title": f"{review} {'fact' if review == 1 else 'facts'} to review",
                "detail": "From uploads",
                "href": "/sources",
                "person": None,
            }
        )
    return sorted(items, key=lambda i: SEVERITY[i["severity"]])


async def build(graph: Graph) -> dict[str, Any]:
    now = now_ms()
    people = await analysis.people(graph)
    active = [p for p in people if p["status"] == "active"]
    handovers = await _handovers(graph, now)
    leaving_ids = {h["employee_id"] for h in handovers if h["status"] != "transferred"}

    # Detail for people who hold the most on their own (bounded work: risk-ranked, top 8).
    ranked = sorted(active, key=lambda p: p["risk"], reverse=True)
    detail_ids = [p["id"] for p in ranked[:8]]
    details = await asyncio.gather(*(analysis.person(graph, pid) for pid in detail_ids))
    people_detail = {pid: d for pid, d in zip(detail_ids, details, strict=False) if d}

    # Knowledge health: the same gap rules a handover runs, across everyone active.
    health: Counter[str] = Counter()
    examples: dict[str, str] = {}
    seen: set[tuple[str, str]] = set()
    for p in active:
        for g in await analysis.find_gaps(graph, p["id"]):
            key = {
                "G1": "unexplained",
                "G6": "contradictions",
                "G8": "procedures",
                "G2": "undocumented",
            }.get(g.rule)
            if key and (key, g.target) not in seen:  # the same item can be a gap for several people
                seen.add((key, g.target))
                health[key] += 1
                examples.setdefault(key, g.title)

    totals: Counter[str] = Counter()
    for p in active:
        totals.update(p.get("sole") or {})

    start = now - HEATMAP_WEEKS * 7 * DAY_MS
    days: Counter[str] = Counter()
    for row in await graph.read("dash_activity", {"from": start, "to": now}):
        days[_day(row["at"])] += 1
    kinds = await graph.read("dash_source_kinds", {})
    review = (await graph.one("dash_review_count", {}) or {}).get("n", 0)

    return {
        "now": now,
        "company": "Northwind",
        "headcount": {
            "active": len(active),
            "leaving": len(leaving_ids),
            "joining": sum(1 for p in people if p["status"] == "incoming"),
            "departed": sum(1 for p in people if p["status"] == "departed"),
        },
        "attention": _attention(handovers, people_detail, review, now),
        "handovers": [
            {k: v for k, v in h.items() if k != "open_access"}
            | {"open_access": len(h["open_access"])}
            for h in handovers
        ],
        "risk": {
            "total": sum(totals.values()),
            "by_kind": {
                k: totals.get(k, 0)
                for k in ("responsibilities", "accounts", "relationships", "knowledge")
            },
            "people": [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "title": p["title"],
                    "team": p["team"],
                    "risk": p["risk"],
                    "sole": p["sole"],
                    "leaving": p["id"] in leaving_ids,
                }
                for p in ranked
                if p["risk"] > 0
            ][:8],
            "teams": await graph.read("dash_team_coverage", {"now": now}),
        },
        "health": {
            k: {"count": health.get(k, 0), "example": examples.get(k)}
            for k in ("unexplained", "contradictions", "procedures", "undocumented")
        },
        "activity": {
            "start": start,
            "days": dict(sorted(days.items())),
            "total": sum(r["n"] for r in kinds),
            "kinds": kinds,
            "review": review,
        },
        "joiners": await graph.read("dash_joiners", {}),
    }
