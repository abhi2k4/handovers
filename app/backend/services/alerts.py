"""Alerts: who hears about what, how and when.

Routing is pure (mode per kind, quiet hours), so it is unit-testable. `notify` records every alert
in the graph and sends it on WhatsApp when the person gave a number, wants it instantly and it is
not quiet time. Button ids are `action:arg`; on WhatsApp they are prefixed with the alert id.
"""

import json
import uuid
from typing import Any

from core.clock import now_ms
from core.config import get_settings
from core.graph import Graph
from core.logging import get_logger
from services import delivery, email, org_policy, whatsapp

log = get_logger(__name__)

KINDS: dict[str, dict[str, Any]] = {
    "resignation": {"label": "Someone resigns", "default": "instant"},
    "reminder": {"label": "You're reminded of a handover task", "default": "instant"},
    "approval": {"label": "A handover waits for your approval", "default": "instant"},
    "lastday": {"label": "A last day is close and the handover isn't ready", "default": "instant"},
    "candidate": {"label": "A strong candidate applies", "default": "instant"},
    "digest": {"label": "Daily summary at 9:00", "default": "instant"},
}
MODES = ("instant", "digest", "off")
CRITICAL = {"lastday"}  # sent even in quiet hours
QUIET = (21, 9)  # 21:00 to 09:00 in the organisation's time zone (policy)
IST_OFFSET_MS = 330 * 60 * 1000


def modes_of(raw: str | None) -> dict[str, str]:
    saved = json.loads(raw) if raw else {}
    return {k: saved.get(k, v["default"]) for k, v in KINDS.items()}


def hour_ist(now: int) -> int:
    return ((now + IST_OFFSET_MS) // 3_600_000) % 24


def is_quiet(hour: int, start: int, end: int) -> bool:
    if start == end:
        return False
    return hour >= start or hour < end if start > end else start <= hour < end


def quiet_now(kind: str, settings: dict[str, Any], hour: int) -> bool:
    start = settings.get("quiet_from", QUIET[0])
    end = settings.get("quiet_to", QUIET[1])
    return kind not in CRITICAL and is_quiet(hour, start, end)


def route(
    kind: str,
    settings: dict[str, Any],
    now: int,
    whatsapp_on: bool,
    hour: int | None = None,
    email_on: bool = False,
) -> str:
    """off | digest | app (in-app only) | held (quiet hours) | whatsapp.

    `hour` is the local hour in the organisation's time zone (IST when not given). Quiet hours
    hold every channel that would wake someone: WhatsApp and email both wait, and the release
    job sends them in the morning (services/notices.release_held).
    """
    mode = modes_of(settings.get("modes"))[kind]
    if mode == "off":
        return "off"
    if mode == "digest" and kind != "digest":
        return "digest"
    wa = whatsapp_on and bool(settings.get("phone"))
    mail = email_on and bool(settings.get("email", True))
    if not wa and not mail:
        return "app"
    if quiet_now(kind, settings, hour_ist(now) if hour is None else hour):
        return "held"
    return "whatsapp" if wa else "app"


def resignation_recipients(
    hr: list[str], manager: str | None, caller: str | None
) -> list[tuple[str, bool]]:
    """Who hears that someone resigned: HR, and the leaver's manager (flagged), once each.

    The person who started the handover already knows. The manager owns the successor choice and
    the transfer approval, so they hear on day one.
    """
    out = [(h, False) for h in dict.fromkeys(hr) if h not in (caller, manager)]
    if manager and manager != caller:
        out.append((manager, True))  # also in HR: they hear once, as the manager
    return out


def wa_text(title: str, body: str) -> str:
    return f"*{title}*\n{body}"


async def settings_for(graph: Graph, emp: str) -> dict[str, Any]:
    row = await graph.one("alert_settings_get", {"emp": emp}) or {}
    return {
        "phone": row.get("phone") or "",
        "email": row.get("email") is not False,  # on unless the person turned it off
        "modes": modes_of(row.get("modes")),
        "quiet_from": row.get("quiet_from") if row.get("quiet_from") is not None else QUIET[0],
        "quiet_to": row.get("quiet_to") if row.get("quiet_to") is not None else QUIET[1],
    }


async def save_settings(graph: Graph, emp: str, settings: dict[str, Any]) -> None:
    await graph.run(
        "alert_settings_set",
        {
            "emp": emp,
            "phone": settings.get("phone") or "",
            "email": bool(settings.get("email", True)),
            "modes": json.dumps(modes_of(json.dumps(settings.get("modes") or {}))),
            "quiet_from": int(settings.get("quiet_from", QUIET[0])),
            "quiet_to": int(settings.get("quiet_to", QUIET[1])),
            "now": now_ms(),
        },
    )


async def deliver(
    graph: Graph,
    channel: Any,
    s: dict[str, Any],
    aid: str,
    to: str,
    title: str,
    body: str,
    buttons: list[dict[str, str]],
    href: str,
    status: str,
) -> tuple[str, str | None]:
    """Send one alert now: WhatsApp when routed there, and email when the channel is on and the
    person has not turned it off. Best effort: a failed email never stops the alert."""
    error = None
    if status == "whatsapp":
        try:
            prefixed = [{**b, "id": f"{aid}|{b['id']}"} for b in buttons]
            await whatsapp.send(s["phone"], wa_text(title, body), prefixed, channel)
            status = "sent"
        except whatsapp.SendError as exc:
            status, error = "failed", str(exc)
    if channel.email_enabled and s.get("email"):
        address = (await graph.one("employee_email", {"emp": to}) or {}).get("email")
        if address:
            link = get_settings().app_url(href) if href else ""
            try:
                await email.send(channel, address, title, body, link)
            except email.SendError as exc:
                log.warning("alert_email_failed", alert=aid, error=str(exc))
    return status, error


async def notify(
    graph: Graph,
    kind: str,
    to: str,
    title: str,
    body: str,
    buttons: list[dict[str, str]] | None = None,
    href: str = "",
    handover: str | None = None,
    step: str | None = None,
) -> dict[str, Any]:
    s = await settings_for(graph, to)
    now = now_ms()
    # The platform admin's WhatsApp settings and master switch (services/delivery.py).
    channel = await delivery.effective(graph, get_settings())
    hour = org_policy.local_hour(await org_policy.load(graph), now)
    status = route(
        kind,
        {**s, "modes": json.dumps(s["modes"])},
        now,
        channel.whatsapp_enabled,
        hour,
        channel.email_enabled,
    )
    if status == "off":
        return {"status": "off", "to": to}
    aid = f"al:{uuid.uuid4().hex[:10]}"
    buttons = buttons or []
    error = None
    if status in ("whatsapp", "app"):
        status, error = await deliver(
            graph, channel, s, aid, to, title, body, buttons, href, status
        )
    await graph.run(
        "alert_add",
        {
            "id": aid,
            "kind": kind,
            "now": now,
            "to": to,
            "status": status,
            "title": title,
            "body": body,
            "buttons": json.dumps(buttons),
            "href": href,
            "error": error,
            "handover": handover,
            "step": step,
        },
    )
    return {"id": aid, "status": status, "to": to}


def days_text(days: int) -> str:
    return "today" if days <= 0 else "tomorrow" if days == 1 else f"in {days} days"


def reminder(item: dict[str, Any], h: dict[str, Any], by: str, days_left: int) -> dict[str, Any]:
    """The message for one readiness step: kind, title, body and buttons."""
    leaver = (h.get("employee") or "").split(" ")[0] or "The leaver"
    hid = h["id"]
    last_day = f"Last day {days_text(days_left)}."
    open_btn = {"id": f"open:{item['href']}", "label": "Open"}
    if item["key"] == "transfer":
        return {
            "kind": "approval",
            "title": f"Approve {leaver}'s knowledge transfer",
            "body": f"{by} is waiting on you. {last_day}",
            "buttons": [{"id": f"approve:{hid}", "label": "Approve"}, open_btn],
        }
    if item["key"] == "ramp":
        return {
            "kind": "approval",
            "title": f"Review the ramp-up plan for {leaver}'s successor",
            "body": f"{by} is waiting on you. {last_day}",
            "buttons": [open_btn],
        }
    return {
        "kind": "reminder",
        "title": f"{item['label']}? ({leaver})",
        "body": f"{by} reminded you: {item['detail']}. {last_day}",
        "buttons": [open_btn, {"id": f"snooze:{item['key']}", "label": "Remind me tomorrow"}],
    }


def digest_text(handovers: list[dict[str, Any]], held: int) -> tuple[str, str]:
    """The daily summary: numbers first."""
    open_ = [h for h in handovers if h.get("status") != "transferred"]
    blocked = [h for h in open_ if not h.get("ready") and h.get("days_left", 99) <= 7]
    soonest = min(open_, key=lambda h: h.get("days_left", 99), default=None)
    parts = [f"Exits: {len(open_)} in progress", f"{len(blocked)} at risk"]
    if soonest:
        first = (soonest.get("employee") or "").split(" ")[0]
        parts.append(f"next last day: {first}, {days_text(soonest['days_left'])}")
    body = " · ".join(parts)
    if held:
        body += f"\n{held} alert{'s' if held != 1 else ''} waiting for you."
    return "Handovers today", body


def is_due(h: dict[str, Any]) -> bool:
    """Last day within a week and not ready: worth an alert even at night."""
    return h.get("status") != "transferred" and not h.get("ready") and h.get("days_left", 99) <= 7
