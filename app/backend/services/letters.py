"""The relieving letter: HR's final sign-off on an exit.

It is drafted from the graph once clearance is complete and the transfer is approved, can only go
out on (or after) the last day when the policy says so, and the leaver sees it only once it is
sent. HR edits the email in the app and sends it, or schedules it for the last day (a `letter`
job). `gate` is pure.
"""

from datetime import datetime
from typing import Any

from core.clock import now_ms
from core.config import get_settings
from core.graph import Graph
from services import access, clearance, delivery, email, org_policy

COMPANY = "Northwind"


def gate(h: dict[str, Any], complete: bool, p: dict[str, Any], now: int) -> dict[str, Any]:
    """Whether the letter can be sent now; if not, why, and from when."""
    if h.get("letter_sent_at"):
        return {"can_send": False, "reason": "Already sent.", "ready_at": None}
    if h.get("status") == "cancelled":
        return {"can_send": False, "reason": "The handover was cancelled.", "ready_at": None}
    missing = []
    if not complete:
        missing.append("every clearance row is confirmed")
    if h.get("status") != "transferred":
        missing.append("the knowledge transfer is approved")
    if missing:
        return {
            "can_send": False,
            "reason": "Ready when " + " and ".join(missing) + ".",
            "ready_at": None,
        }
    if p.get("letter_on_last_day") and now < (h.get("effective_at") or 0):
        return {
            "can_send": False,
            "reason": "Company policy: the relieving letter goes out on the last day.",
            "ready_at": h.get("effective_at"),
        }
    return {"can_send": True, "reason": "", "ready_at": None}


def email_draft(letter: dict[str, Any], to: str | None, company: str = COMPANY) -> dict[str, Any]:
    """The email HR sends, as plain text they can edit."""
    first = letter["to"].split(" ")[0]
    body = "\n\n".join(
        [
            f"Dear {first},",
            *letter["body"],
            "Your relieving letter is attached below for your records.",
            f"Warm regards,\n{letter['signatory']['name']}\n{letter['signatory']['title']}, {company}",
        ]
    )
    return {"to": to or "", "subject": f"Relieving letter, {letter['to']}", "body": body}


async def signatory(graph: Graph) -> dict[str, str]:
    hr = (await access.hr_people(graph) or [{}])[0]
    return {"name": hr.get("name") or "HR", "title": hr.get("title") or "Human Resources"}


async def build(graph: Graph, h: dict[str, Any]) -> dict[str, Any]:
    p = await org_policy.load(graph)
    return clearance.letter(h, COMPANY, await signatory(graph), now_ms(), org_policy.zone(p))


async def send(graph: Graph, hid: str, by: str, draft: dict[str, Any]) -> dict[str, Any]:
    """Send now (the button, or the scheduled job on the last day). Checks the gate again."""
    from services import alerts
    from services import handover as svc

    h = await svc.get(graph, hid)
    p = await org_policy.load(graph)
    items = await clearance.load(graph, hid)
    confirmed, total = clearance.counts(items)
    g = gate(h, total > 0 and confirmed == total, p, now_ms())
    if not g["can_send"]:
        raise svc.Conflict(g["reason"])
    letter = await build(graph, h)
    default = email_draft(letter, h.get("employee_email"))
    subject = (draft.get("subject") or default["subject"]).strip()
    body = (draft.get("body") or default["body"]).strip()
    to = h.get("employee_email") or ""
    emailed = False
    channel = await delivery.effective(graph, get_settings())
    if to and channel.email_enabled:
        letter_text = "\n\n".join(
            [
                letter["date"],
                f"To {letter['to']}",
                letter["subject"],
                *letter["body"],
                f"{letter['signatory']['name']}\n{letter['signatory']['title']}",
            ]
        )
        try:
            await email.send(channel, to, subject, f"{body}\n\n---\n\n{letter_text}")
            emailed = True
        except email.SendError:
            emailed = False
    await graph.run(
        "letter_sent", {"id": hid, "now": now_ms(), "by": by, "subject": subject, "to": to}
    )
    await svc.audit(
        graph, hid, "letter.sent", {"to": to, "emailed": emailed, "subject": subject}, by
    )
    await alerts.notify(
        graph,
        "reminder",
        h["employee_id"],
        "Your relieving letter is ready",
        f"{letter['signatory']['name']} sent it{' to ' + to if emailed else ''}. You can also open it in Handovers.",
        [{"id": "open:/", "label": "Open"}],
        "/",
        hid,
    )
    return {"sent": True, "emailed": emailed, "to": to, "at": datetime.now().isoformat()}
