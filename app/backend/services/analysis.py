"""Read models over the graph: a person's work memory, org risk, and handover gaps.

Everything here is graph queries plus pure policy; no LLM decides anything.
"""

from typing import Any

from core.clock import now_ms
from core.graph import Graph
from services import policy


async def people(graph: Graph) -> list[dict[str, Any]]:
    now = now_ms()
    rows = await graph.read("people_list", {})
    risk: dict[str, dict[str, int]] = {}
    for kind, query in (
        ("responsibilities", "risk_sole_responsibilities"),
        ("accounts", "risk_sole_accounts"),
        ("relationships", "risk_sole_stakeholders"),
        ("knowledge", "risk_sole_knowledge"),
    ):
        for r in await graph.read(query, {"now": now}):
            risk.setdefault(r["employee"], {})[kind] = int(r["n"])
    seen: set[str] = set()
    out = []
    for r in rows:
        if r["id"] in seen:  # one row per person even if several handovers matched
            continue
        seen.add(r["id"])
        sole = risk.get(r["id"], {})
        out.append({**r, "sole": sole, "risk": sum(sole.values())})
    return out


async def person(graph: Graph, emp: str, at: int | None = None) -> dict[str, Any] | None:
    """What `emp` holds now, or at time `at` (e.g. just before their work moved to a successor)."""
    now = at or now_ms()
    info = await graph.one("person_get", {"emp": emp})
    if not info or not info.get("id"):
        return None
    eod_total = (await graph.one("person_eod_count", {"emp": emp}) or {}).get("n", 0)
    responsibilities = await graph.read("person_responsibilities", {"emp": emp, "now": now})
    for r in responsibilities:
        r["share"] = policy.share(r.get("eods") or 0, eod_total)
        due, overdue = policy.next_due(r.get("last_seen"), r.get("cadence"), now)
        r["next_due"], r["overdue"] = due, overdue
    knowledge = await graph.read("person_knowledge", {"emp": emp, "now": now})
    return {
        **info,
        "eod_total": eod_total,
        "responsibilities": responsibilities,
        "accounts": await graph.read("person_accounts", {"emp": emp, "now": now}),
        "stakeholders": await graph.read("person_stakeholders", {"emp": emp, "now": now}),
        "knowledge": knowledge,
        "skills": await graph.read("person_skills", {"emp": emp}),
        "open_work": await graph.read("person_open_work", {"emp": emp}),
        "recent": await graph.read("person_sources", {"emp": emp, "limit": 12}),
    }


async def find_gaps(graph: Graph, emp: str) -> list[policy.GapSeed]:
    """Run every gap rule for one person and return deduplicated, prioritised gaps."""
    now = now_ms()
    params = {
        "emp": emp,
        "now": now,
        "predicates": policy.RATIONALE_PREDICATES,
        "floor": policy.WEAK_CONFIDENCE,
        "min_repeats": policy.MIN_REPEATS,
    }
    seeds: list[policy.GapSeed] = []

    def add(
        rule: str, kind: str, rows: list[dict[str, Any]], context_key: str | None = None
    ) -> None:
        for r in rows:
            seeds.append(
                policy.GapSeed(
                    rule=rule,
                    target=r["target"],
                    target_kind=kind,
                    title=r.get("title") or "",
                    question=policy.seed_question(rule, r),
                    priority=policy.priority(rule, r.get("confidence")),
                    context=str(r.get(context_key) or "") if context_key else "",
                )
            )

    g1_claims = await graph.read("gap_g1_claims", params)
    add("G1", "Claim", g1_claims)
    add("G1", "Decision", await graph.read("gap_g1_decisions", params))
    add("G2", "Knowledge", await graph.read("gap_g2_undocumented", params))
    add("G4", "Knowledge", await graph.read("gap_g4_weak", params))
    # A contradiction targets the stale side (the one without a G1 question already), so both the
    # "why" and the "which is current" questions survive deduplication.
    g1_targets = {r["target"] for r in g1_claims}
    seen_pairs: set[frozenset[str]] = set()
    unique_contradictions = []
    for r in await graph.read("gap_g6_contradictions", params):
        pair = frozenset((r["target"], r["other"]))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        if r["target"] in g1_targets:
            r = {
                **r,
                "target": r["other"],
                "other": r["target"],
                "title": r["other_title"],
                "other_title": r["title"],
                "value": r["other_value"],
                "other_value": r["value"],
            }
        unique_contradictions.append({**r, "context": r["other"]})
    add("G6", "Claim", unique_contradictions, "context")
    add("G7A", "Account", await graph.read("gap_g7_accounts", params), "system")
    add("G7S", "Stakeholder", await graph.read("gap_g7_stakeholders", params), "context")
    add("G8", "Responsibility", await graph.read("gap_g8_recurring_fix", params))
    add("G7R", "Responsibility", await graph.read("gap_g7_responsibilities", params), "cadence")
    return policy.dedupe_gaps(seeds)
