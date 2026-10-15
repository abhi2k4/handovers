"""Pure, I/O-free policy: gap weights, question templates, cadence maths, transfer rules.

Kept free of I/O so every rule here is unit-testable and explainable.
"""

from dataclasses import dataclass
from typing import Any

from core.clock import DAY_MS

# Predicates whose value is a choice someone made, so a missing "why" is a real gap.
RATIONALE_PREDICATES = [
    "retry_limit",
    "cac_target",
    "budget_split",
    "schedule",
    "threshold",
    "timeout",
    "limit",
    "target",
    "price",
    "sla",
    "frequency",
]
WEAK_CONFIDENCE = 0.6
MIN_REPEATS = 2
INTERVIEW_SIZE = 8

# Higher = asked first. Sole access breaks first (lockouts, billing), then the missing "why".
RULE_WEIGHT = {
    "G7A": 1.0,  # sole admin of an account
    "G1": 0.95,  # current setting or decision with no recorded reason
    "G8": 0.9,  # recurring fix with no procedure
    "G6": 0.85,  # contradicting sources
    "G7S": 0.8,  # sole external relationship
    "G2": 0.6,  # undocumented decision or procedure
    "G4": 0.5,  # weakly supported
    "G7R": 0.4,  # sole owner of a responsibility (plan item, not an interview question)
}
RULE_LABEL = {
    "G7A": "Only admin",
    "G1": "No reason recorded",
    "G8": "Fixed repeatedly, never written down",
    "G6": "Sources disagree",
    "G7S": "Only contact",
    "G2": "Not written down",
    "G4": "Thin evidence",
    "G7R": "Only owner",
    "M": "Asked of every leaver",
    "Q": "Asked by HR or the manager",
}
INTERVIEW_RULES = {"G7A", "G1", "G8", "G6", "G7S", "G2", "G4", "M", "Q"}
# The exit interview leads with the "why" and "how" questions the graph found, then the
# company's standard questions and anything HR or the manager asked; access questions follow.
INTERVIEW_ORDER = {"G1": 0, "G8": 1, "G6": 2, "M": 3, "Q": 4, "G7A": 5, "G7S": 6, "G2": 7, "G4": 8}

CADENCE_DAYS = {"daily": 1, "weekly": 7, "biweekly": 14, "monthly": 31, "quarterly": 92}


@dataclass(frozen=True)
class GapSeed:
    rule: str
    target: str
    target_kind: str
    title: str
    question: str
    priority: float
    context: str = ""


def seed_question(rule: str, row: dict[str, Any]) -> str:
    title = row.get("title") or ""
    if rule == "G1" and row.get("predicate"):
        prev = row.get("previous")
        change = f", and why did it change from {prev}" if prev else ""
        return f"“{title}”. Why is it set this way{change}?"
    if rule == "G1":
        return f"You decided to {title[0].lower() + title[1:]}. What was the reason, and when should someone revisit it?"
    if rule == "G2":
        return f"“{title}” isn't written down anywhere. What should the next person know about it?"
    if rule == "G4":
        return f"Is this still true: “{title}”? What confirms it?"
    if rule == "G6":
        return (
            f"Two sources disagree: {row.get('value')} vs {row.get('other_value')}. "
            f"Which is current, and since when?"
        )
    if rule == "G7A":
        return (
            f"You're the only admin on {title}. Who should take it over, and is anything tied to it "
            f"(billing, recovery email, two-factor)?"
        )
    if rule == "G7S":
        org = f" at {row['org']}" if row.get("org") else ""
        return f"You're the only one who works with {title}{org}. What should the next person know about this relationship?"
    if rule == "G8":
        return f"You've handled “{title}” {row.get('fixes')} times and the steps aren't written down. What are they?"
    if rule == "G7R":
        return f"Nobody else does “{title}”. Who should pick it up?"
    return title


def priority(rule: str, confidence: float | None = None) -> float:
    weight = RULE_WEIGHT.get(rule, 0.3)
    # Less certain knowledge is slightly more urgent to confirm.
    bump = 0.0 if confidence is None else (1 - min(max(confidence, 0.0), 1.0)) * 0.04
    return round(weight + bump, 4)


def dedupe_gaps(seeds: list[GapSeed]) -> list[GapSeed]:
    """One gap per target, keeping the highest-priority rule."""
    best: dict[str, GapSeed] = {}
    for s in seeds:
        if s.target not in best or s.priority > best[s.target].priority:
            best[s.target] = s
    return sorted(best.values(), key=lambda s: s.priority, reverse=True)


def next_due(last_seen: int | None, cadence: str | None, now: int) -> tuple[int | None, bool]:
    """Next expected occurrence of recurring work, and whether it is already overdue."""
    if not last_seen or not cadence or cadence not in CADENCE_DAYS:
        return None, False
    due = last_seen + CADENCE_DAYS[cadence] * DAY_MS
    return due, due < now


def share(eods: int, total: int) -> float:
    return round(eods / total, 3) if total else 0.0


# ---- transfer projection ------------------------------------------------------------------------


def transfer_decision(item: dict[str, Any]) -> tuple[bool, str]:
    """Include or exclude one candidate knowledge item. First matching reason wins."""
    if item.get("sensitivity") == "personal":
        return False, "personal"
    if item.get("private"):
        return False, "kept private"
    if item.get("already_held"):
        return False, "already known"
    if (item.get("confidence") or 0) < 0.4:
        return False, "low confidence"
    return True, "current" if item.get("current") else "history"
