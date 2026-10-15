"""Handover readiness: what still blocks the last day, who owns it, and the next action.

Pure: built from data the handover services already read, so it is unit-testable and every check
links to the screen where it is resolved.
"""

from typing import Any

from core.clock import DAY_MS
from services import access, handover_rules

# Short names for compact step lists (the HR overview).
SHORT = {
    "successor": "Successor",
    "access": "Accounts",
    "interview": "Exit interview",
    "hiring": "Job description",
    "ramp": "Ramp-up plan",
    "transfer": "Transfer",
    "clearance": "Clearance",
}

# The exit pipeline: each stage is done when its checks are (greytHR/Keka-style named stages).
STAGES = [
    ("notice", "Notice", {"successor"}),
    ("capture", "Capture", {"interview"}),
    ("handover", "Handover", {"hiring", "ramp", "transfer"}),
    ("clearance", "Clearance", {"access", "clearance"}),
]


def stages(items: list[dict[str, Any]], days_left: int) -> list[dict[str, Any]]:
    """Every stage with its state: done, current (the first unfinished) or todo."""
    done = {i["key"] for i in items if i["done"]}
    out, current = [], False
    for key, label, checks in STAGES:
        finished = checks <= done
        state = "done" if finished and not current else "todo" if current else "current"
        current = current or state == "current"
        out.append({"key": key, "label": label, "state": state})
    exited = "todo" if current else ("done" if days_left == 0 else "current")
    out.append({"key": "exited", "label": "Exited", "state": exited})
    return out


# Who can act on each check; everyone else sees it as "waiting on <owner>".
ACTOR = {
    "successor": access.can_run_handover,
    "access": access.can_reassign_account,
    "interview": access.can_answer,
    "hiring": access.can_run_handover,
    "ramp": access.can_approve,
    "transfer": access.can_approve,
    "clearance": access.can_run_handover,
}


def build(
    h: dict[str, Any],
    artifacts: set[str],
    ramp_status: str | None,
    now: int,
    pending: int = 0,
    clearance: tuple[int, int] = (0, 0),
    proposals: int = 0,
) -> dict[str, Any]:
    """`pending`: knowledge captured since the transfer was approved, waiting for a follow-up.
    `clearance`: (confirmed, total) clearance rows. `proposals`: account handovers waiting for HR.

    An account counts as reassigned only when someone else actually holds its admin in the graph
    (the gap's resolution is `reassigned`), never because its interview question was answered.
    The interview waits on the required questions only (mandatory, asked, top found ones).
    """
    gaps = h.get("gaps") or []
    leaver = h.get("employee") or "The leaver"
    approver = (h.get("approver") or {}).get("name") or h.get("manager") or "Their manager"
    hid = h["id"]

    accounts = [g for g in gaps if g["rule"] == "G7A"]
    accounts_open = sum(1 for g in accounts if g.get("resolution") != "reassigned")
    questions, _ = handover_rules.interview_sets(gaps)
    answered = sum(1 for g in questions if g["status"] == "answered")
    transferred = h.get("status") == "transferred"
    rejected = (h.get("transfer") or {}).get("decision") == "rejected" and not transferred

    def item(
        key: str, label: str, done: bool, detail: str, owner: str, action: str, href: str
    ) -> dict[str, Any]:
        return {
            "key": key,
            "label": label,
            "short": SHORT[key],
            "done": done,
            "detail": detail,
            "owner": owner,
            "action": None if done else action,
            "href": href,
        }

    items = [
        item(
            "successor",
            "Successor chosen",
            bool(h.get("successor_id")),
            h.get("successor") or "Not chosen yet",
            "HR",
            "Choose successor",
            f"/handovers/{hid}",
        ),
        item(
            "access",
            "Sole-admin accounts reassigned",
            accounts_open == 0,
            f"{len(accounts) - accounts_open} of {len(accounts)} reassigned"
            + (f" · {proposals} waiting for HR" if proposals else ""),
            "IT",
            "Reassign accounts",
            "/accounts",
        ),
        item(
            "interview",
            "Exit interview answered",
            bool(questions) and answered == len(questions),
            f"{answered} of {len(questions)} questions",
            leaver,
            "Open interview",
            f"/handovers/{hid}?tab=interview",
        ),
        item(
            "hiring",
            "Job description ready",
            "jd" in artifacts,
            "Generated" if "jd" in artifacts else "Not generated",
            "HR",
            "Generate",
            f"/handovers/{hid}?tab=jd",
        ),
        item(
            "ramp",
            "Ramp-up plan approved",
            ramp_status == "approved",
            {"approved": "Approved", "draft": "Draft waiting for review"}.get(
                ramp_status or "", "Not created"
            ),
            approver,
            "Review plan",
            f"/handovers/{hid}?tab=ramp",
        ),
        item(
            "transfer",
            "Knowledge transfer approved",
            transferred and not pending,
            (f"{pending} new since approval" if pending else "Approved")
            if transferred
            else f"Sent back: {(h.get('transfer') or {}).get('comment') or 'see the transfer'}"
            if rejected
            else f"Waiting for {approver}",
            approver,
            "Send new items" if transferred else "Review transfer",
            f"/handovers/{hid}?tab=transfer",
        ),
        item(
            "clearance",
            "Clearance complete",
            clearance[1] > 0 and clearance[0] == clearance[1],
            f"{clearance[0]} of {clearance[1]} confirmed" if clearance[1] else "Not started",
            "HR",
            "Open clearance",
            f"/handovers/{hid}?tab=clearance",
        ),
    ]
    done = sum(1 for i in items if i["done"])
    effective = h.get("effective_at") or now
    days_left = max(0, round((effective - now) / DAY_MS))
    pipeline = stages(items, days_left)
    return {
        "handover": hid,
        "days_left": days_left,
        "stages": pipeline,
        "stage": next((st["key"] for st in pipeline if st["state"] != "done"), "exited"),
        "done": done,
        "total": len(items),
        "ready": done == len(items),
        "items": items,
    }


def for_caller(r: dict[str, Any], caller: access.Caller | None, leaver_id: str) -> dict[str, Any]:
    """Mark the checks this caller can act on (`mine`); the UI offers actions only on those."""
    items = [i | {"mine": not i["done"] and ACTOR[i["key"]](caller, leaver_id)} for i in r["items"]]
    return r | {"items": items}
