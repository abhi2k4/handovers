"""Pure rules for a handover's life: who may succeed, until when it can be cancelled, which
questions the leaver must answer, and how to use the days left. No I/O, so each rule is
unit-tested and every refusal can be explained in one sentence.
"""

import math
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from core.clock import DAY_MS
from services import policy

# ---- successor -----------------------------------------------------------------------------------


def successor_problem(leaver: dict[str, Any], cand: dict[str, Any] | None) -> dict[str, Any] | None:
    """Why `cand` should not take over `leaver`'s work, or None if they can.

    `blocking` problems refuse the choice. A successor from another team is a warning: the
    person who chooses must confirm it, because pulling someone across teams leaves a gap there
    and changes how both teams work.
    """
    if cand is None:
        return {
            "code": "not_found",
            "blocking": True,
            "message": "That person is not in the directory.",
        }
    name = cand.get("name") or "This person"
    if cand["id"] == leaver["id"]:
        return {
            "code": "self",
            "blocking": True,
            "message": "The leaver can't be their own successor.",
        }
    if cand.get("status") == "departed":
        return {
            "code": "departed",
            "blocking": True,
            "message": f"{name} has already left the company.",
        }
    if cand.get("leaving"):
        return {
            "code": "leaving",
            "blocking": True,
            "message": f"{name} is leaving too. Their own work will need a successor.",
        }
    if leaver.get("team_id") and cand.get("team_id") and cand["team_id"] != leaver["team_id"]:
        theirs = cand.get("team") or "another team"
        ours = leaver.get("team") or "the leaver's team"
        return {
            "code": "other_team",
            "blocking": False,
            "message": (
                f"{name} is in {theirs}, not {ours}. Moving them leaves a gap in {theirs} and "
                f"changes how both teams work. Their manager should agree first."
            ),
        }
    return None


# ---- cancellation (withdrawn resignation) --------------------------------------------------------


def cancel_window(h: dict[str, Any], p: dict[str, Any], now: int) -> dict[str, Any]:
    """Whether the handover can still be cancelled, and until when (the organisation's
    withdrawal window, never past the approved transfer or the last day)."""
    if h.get("status") == "cancelled":
        return {"allowed": False, "until": None, "reason": "Already cancelled."}
    if h.get("status") == "transferred":
        return {
            "allowed": False,
            "until": None,
            "reason": "The transfer is approved, so the handover can no longer be withdrawn.",
        }
    days = int(p.get("withdrawal_days") or 0)
    until = min((h.get("created_at") or now) + days * DAY_MS, h.get("effective_at") or now)
    if now > until:
        return {
            "allowed": False,
            "until": until,
            "reason": f"Company policy allows withdrawing a resignation within {days} days. That window has closed.",
        }
    return {"allowed": True, "until": until, "reason": ""}


# ---- the exit interview --------------------------------------------------------------------------

MANDATORY = "M"  # asked of every leaver (the policy's list); never dismissed
ASKED = "Q"  # added by HR or the manager, including follow-ups on an answer


def interview_sets(
    gaps: list[dict[str, Any]], limit: int = policy.INTERVIEW_SIZE
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(core, extra). Core: every mandatory and asked question plus the top `limit` questions the
    graph found; readiness waits on these. Extra: the rest of what the graph found, for the days
    left once the core is done."""
    live = [g for g in gaps if g["rule"] in policy.INTERVIEW_RULES and g["status"] != "dismissed"]

    def order(g: dict[str, Any]) -> tuple[int, float]:
        return (policy.INTERVIEW_ORDER.get(g["rule"], 9), -(g.get("priority") or 0))

    fixed = [g for g in live if g["rule"] in (MANDATORY, ASKED)]
    found = sorted((g for g in live if g["rule"] not in (MANDATORY, ASKED)), key=order)
    core = sorted(fixed + found[:limit], key=order)
    return core, found[limit:]


# ---- the days left -------------------------------------------------------------------------------


def capture_plan(
    now: int,
    effective_at: int,
    tz: ZoneInfo,
    core_open: list[dict[str, Any]],
    extra_open: list[dict[str, Any]],
    recurring: list[dict[str, Any]],
    contacts: list[dict[str, Any]],
    accounts: list[dict[str, Any]],
    successor: str | None,
    solo_work: list[dict[str, Any]] | None = None,
    grouped: bool = False,
) -> dict[str, Any]:
    """A day-by-day plan from today to the last day: what to capture, and from whom.

    Questions are spread over the days before the last two; recurring work due before the last
    day is done together with the successor on its due date; sole contacts are introduced in the
    first third; accounts move two days before the end; the last day is clearance. Once every
    core question is answered the plan keeps going: the extra questions, then walkthroughs of
    work only the leaver does, so no day left is wasted.
    """
    days_left = max(0, math.ceil((effective_at - now) / DAY_MS))
    span = days_left + 1  # today .. last day
    capture_days = max(1, span - 2)
    who = successor.split(" ")[0] if successor else "the successor"
    days: list[list[dict[str, Any]]] = [[] for _ in range(span)]

    questions = core_open + extra_open
    pace = math.ceil(len(core_open) / capture_days) if core_open else 0
    per_day = max(1, math.ceil(len(questions) / capture_days)) if questions else 0
    batches: dict[int, list[tuple[int, dict[str, Any]]]] = {}
    for i, g in enumerate(questions):
        day = min(i // per_day, capture_days - 1) if per_day else 0
        batches.setdefault(day, []).append((i, g))
    for day, batch in batches.items():
        if grouped:
            # A viewer who may not read the questions (HR) sees how many, not what they ask.
            core_n = sum(1 for i, _ in batch if i < len(core_open))
            labels = sorted({policy.RULE_LABEL.get(g["rule"], "Question") for _, g in batch})
            days[day].append(
                {
                    "kind": "question" if core_n else "extra",
                    "title": f"{len(batch)} exit-interview question{'s' if len(batch) != 1 else ''}",
                    "detail": ", ".join(labels),
                    "tab": "interview",
                }
            )
            continue
        for i, g in batch:
            days[day].append(
                {
                    "kind": "question" if i < len(core_open) else "extra",
                    "title": g.get("title") or g.get("question") or "Question",
                    "detail": policy.RULE_LABEL.get(g["rule"], "Question"),
                    "tab": "interview",
                }
            )
    if not questions:
        # Everything asked is answered: spend the days left on walkthroughs of work only they do.
        for i, r in enumerate(solo_work or []):
            days[min(i, capture_days - 1)].append(
                {
                    "kind": "walkthrough",
                    "title": f"Walk {who} through “{r['title']}”",
                    "detail": "Only they do this",
                    "tab": "plan",
                }
            )
    first_third = max(1, span // 3)
    for i, c in enumerate(contacts):
        days[min(i, first_third - 1)].append(
            {
                "kind": "intro",
                "title": f"Introduce {who} to {c['name']}",
                "detail": c.get("org") or "Only contact",
                "tab": "plan",
            }
        )
    for r in recurring:
        due = r.get("next_due")
        offset = max(0, min(span - 1, math.floor((due - now) / DAY_MS))) if due else 0
        days[offset].append(
            {
                "kind": "shadow",
                "title": f"Do “{r['title']}” together with {who}",
                "detail": "Due before the last day" if due else "Recurring work",
                "tab": "plan",
            }
        )
    for a in accounts:
        days[max(0, span - 3)].append(
            {
                "kind": "access",
                "title": f"Move admin of {a['name']}",
                "detail": "Before the last two days, so nothing locks",
                "tab": "clearance",
            }
        )
    days[span - 1].append(
        {
            "kind": "exit",
            "title": "Clearance and relieving letter",
            "detail": "Access ends today",
            "tab": "clearance",
        }
    )

    def label(offset: int) -> str:
        d = datetime.fromtimestamp((now + offset * DAY_MS) / 1000, tz)
        return f"{d.day} {d.strftime('%b')}"

    covered = not core_open
    if covered and extra_open:
        message = f"Every required answer is in. {len(extra_open)} more questions can still be captured before the last day."
    elif covered:
        message = "Everything the graph found is captured. Use the days left for walkthroughs with the successor."
    else:
        message = f"{len(core_open)} required answers left: about {pace} a day to finish two days before the last day."
    return {
        "days_left": days_left,
        "pace": pace,
        "covered": covered,
        "message": message,
        "days": [
            {"offset": i, "date": label(i), "items": items, "last": i == span - 1}
            for i, items in enumerate(days)
            if items
        ],
    }


# ---- "sources disagree" ----------------------------------------------------------------------------

_CURRENT = (
    "is current",
    "is correct",
    "is right",
    "is the current",
    "is what we use",
    "still holds",
)


def suggest_claim(choices: list[dict[str, Any]], answer: str) -> str | None:
    """Which of two disagreeing claims the leaver's answer names as current, or None if it does
    not say. A value followed by "is current" (or similar) wins; otherwise the one named first.
    Only a suggestion: the leaver confirms the pick before anything is saved."""
    text = answer.lower()
    found: list[tuple[int, int, str]] = []
    for c in choices:
        value = str(c.get("value") or "").strip().lower()
        if not value:
            continue
        at = text.find(value)
        while at != -1:
            # Not part of a longer number ("3" inside "2025").
            before = text[at - 1] if at > 0 else " "
            after = text[at + len(value)] if at + len(value) < len(text) else " "
            if not (before.isdigit() or after.isdigit()):
                tail = text[at + len(value) : at + len(value) + 24]
                strong = any(tail.lstrip(" .,'\"”").startswith(w) for w in _CURRENT)
                found.append((0 if strong else 1, at, c["id"]))
                break
            at = text.find(value, at + 1)
    return min(found)[2] if found else None
