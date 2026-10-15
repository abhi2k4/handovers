"""KPIs for the Insights page and the leadership home (docs/product-strategy.md section 7).

Every number is computed from the graph: process and risk KPIs reuse the dashboard read model, and
outcome KPIs are measured over completed handovers (`kpi_handover_outcomes`). With no completed
handover yet, an outcome has no value rather than a made-up one.
"""

import math
from typing import Any

from core.graph import Graph
from services import dashboard, policy


def _pct(part: float, whole: float) -> int | None:
    # Half up, like Math.round in the UI (Python's round() is banker's rounding: 12.5 -> 12).
    return math.floor(100 * part / whole + 0.5) if whole else None


async def build(graph: Graph) -> dict[str, Any]:
    dash = await dashboard.build(graph)
    open_handovers = [
        h for h in dash["handovers"] if h["status"] not in ("transferred", "cancelled")
    ]
    done_handovers = [h for h in dash["handovers"] if h["status"] == "transferred"]

    gaps_total = sum(h["gaps"] for h in open_handovers)
    gaps_open = sum(int(h["open_gaps"]) for h in open_handovers)
    questions = sum(h["questions"] for h in open_handovers)
    answered = sum(h["answered"] for h in open_handovers)
    access_open = sum(h["open_access"] for h in open_handovers)

    accounts_total = 0
    for h in open_handovers:
        for g in await graph.read("gap_list", {"handover": h["id"]}):
            if g["rule"] == "G7A":
                accounts_total += 1

    teams = dash["risk"]["teams"]
    work_total = sum(t["total"] for t in teams)
    work_sole = sum(t["sole"] for t in teams)

    process = [
        {
            "key": "north_star",
            "label": "Single-person knowledge resolved",
            "value": _pct(gaps_total - gaps_open, gaps_total),
            "unit": "%",
            "target": 100,
            "detail": f"{gaps_total - gaps_open} of {gaps_total} handover gaps closed before the last day",
        },
        {
            "key": "accounts_reassigned",
            "label": "Sole-admin accounts reassigned",
            "value": _pct(accounts_total - access_open, accounts_total),
            "unit": "%",
            "target": 100,
            "detail": f"{access_open} of {accounts_total} still held by someone leaving",
        },
        {
            "key": "exit_capture",
            "label": "Exit-interview answers captured",
            "value": _pct(answered, questions),
            "unit": "%",
            "target": 100,
            "detail": f"{answered} of {questions} questions only the leaver can answer",
        },
        {
            "key": "handovers_completed",
            "label": "Handovers completed",
            "value": len(done_handovers),
            "unit": "",
            "target": None,
            "detail": f"{len(open_handovers)} in progress",
        },
    ]

    risk = [
        {
            "key": "backup_coverage",
            "label": "Work with a backup",
            "value": _pct(work_total - work_sole, work_total),
            "unit": "%",
            "target": 80,
            "detail": f"{int(work_total - work_sole)} of {work_total} responsibilities have two or more holders",
        },
        {
            "key": "held_by_one",
            "label": "Held by one person",
            "value": dash["risk"]["total"],
            "unit": "",
            "target": None,
            "detail": "Responsibilities, accounts, relationships and knowledge with a single holder",
        },
        {
            "key": "unexplained",
            "label": "Settings or decisions with no reason",
            "value": dash["health"]["unexplained"]["count"],
            "unit": "",
            "target": 0,
            "detail": dash["health"]["unexplained"]["example"] or "",
        },
        {
            "key": "contradictions",
            "label": "Contradictions",
            "value": dash["health"]["contradictions"]["count"],
            "unit": "",
            "target": 0,
            "detail": dash["health"]["contradictions"]["example"] or "",
        },
    ]

    return {
        "now": dash["now"],
        "company": dash["company"],
        "headcount": dash["headcount"],
        "process": process,
        "risk": risk,
        "risk_by_kind": dash["risk"]["by_kind"],
        "teams": [
            {
                "id": t["id"],
                "name": t["name"],
                "total": t["total"],
                "sole": int(t["sole"]),
                "coverage": _pct(t["total"] - t["sole"], t["total"]),
            }
            for t in teams
        ],
        "people": dash["risk"]["people"][:8],
        "handovers": open_handovers,
        "outcomes": outcomes(
            await graph.read("kpi_handover_outcomes", {}),
            {h["id"]: await graph.read("gap_list", {"handover": h["id"]}) for h in done_handovers},
        ),
    }


def outcomes(
    rows: list[dict[str, Any]], gaps: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    """Outcome KPIs over completed handovers. Pure: `rows` from `kpi_handover_outcomes`, `gaps`
    per handover id from `gap_list`."""
    done = len(rows)
    on_time = sum(
        1 for r in rows if r["handed_at"] is not None and r["handed_at"] <= r["effective_at"]
    )
    knowledge = sum(int(r["knowledge"] or 0) for r in rows)
    questions = answered = accounts = reassigned = 0
    for r in rows:
        for g in gaps.get(r["id"], []):
            if g["rule"] in policy.INTERVIEW_RULES and g["status"] != "dismissed":
                questions += 1
                answered += g["status"] == "answered"
            if g["rule"] == "G7A":
                accounts += 1
                reassigned += g["status"] != "open"
    none = "No handover completed yet"
    return [
        {
            "key": "on_time",
            "label": "Handed over before the last day",
            "value": _pct(on_time, done),
            "unit": "%",
            "target": 100,
            "detail": f"{on_time} of {done} completed handovers" if done else none,
        },
        {
            "key": "knowledge_passed",
            "label": "Knowledge passed on, approved",
            "value": knowledge if done else None,
            "unit": "",
            "target": None,
            "detail": f"Items successors received in {done} {'handover' if done == 1 else 'handovers'}"
            if done
            else none,
        },
        {
            "key": "exit_answers",
            "label": "Exit questions answered",
            "value": _pct(answered, questions),
            "unit": "%",
            "target": 100,
            "detail": f"{answered} of {questions} in completed handovers" if questions else none,
        },
        {
            "key": "accounts_closed",
            "label": "Sole-admin accounts handled",
            "value": _pct(reassigned, accounts),
            "unit": "%",
            "target": 100,
            "detail": f"{reassigned} of {accounts} closed by the transfer"
            if accounts
            else (none if not done else "None to reassign"),
        },
    ]
