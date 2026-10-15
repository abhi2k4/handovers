"""Scheduled notices: the daily digest, last-day warnings, and alerts held over quiet hours.

These used to run only when HR pressed a button. The job queue (services/jobs.py) now runs them
on time; the buttons still work and call the same functions.
"""

import json
from typing import Any

from core.clock import now_ms
from core.config import get_settings
from core.graph import Graph
from services import access, alerts, dashboard, delivery, org_policy


async def send_digest(graph: Graph) -> list[dict[str, Any]]:
    """Today's summary to every HR person, with how many alerts wait for them."""
    handovers = await dashboard.handovers(graph, now_ms())
    sent = []
    for p in await access.hr_people(graph):
        held = sum(
            1
            for x in await graph.read("alert_list", {"to": p["id"]})
            if x["status"] in {"held", "digest"} and not x["acted"]
        )
        title, body = alerts.digest_text(handovers, held)
        sent.append(
            await alerts.notify(
                graph, "digest", p["id"], title, body, [{"id": "open:/", "label": "Open"}], "/"
            )
        )
    return sent


async def lastday_alerts(graph: Graph) -> list[dict[str, Any]]:
    """A last day within a week and the handover not ready: tell HR and the approver. Critical,
    so it goes out even in quiet hours."""
    handovers = await dashboard.handovers(graph, now_ms())
    routes = await access.approval_routes(graph)
    hr = [p["id"] for p in await access.hr_people(graph)]
    sent = []
    for h in handovers:
        if not alerts.is_due(h):
            continue
        first = h["employee"].split(" ")[0]
        approver = routes.get(h.get("employee_id") or "", {}).get("id")
        for to in dict.fromkeys([*hr, *([approver] if approver else [])]):
            sent.append(
                await alerts.notify(
                    graph,
                    "lastday",
                    to,
                    f"{first}'s last day is {alerts.days_text(h['days_left'])}",
                    f"The handover isn't ready: {sum(s['done'] for s in h['steps'])} of "
                    f"{len(h['steps'])} steps done.",
                    [{"id": f"open:/handovers/{h['id']}", "label": "Open handover"}],
                    f"/handovers/{h['id']}",
                    h["id"],
                )
            )
    return sent


async def release_held(graph: Graph) -> dict[str, int]:
    """Send alerts held during quiet hours to everyone whose quiet hours are over."""
    now = now_ms()
    hour = org_policy.local_hour(await org_policy.load(graph), now)
    channel = await delivery.effective(graph, get_settings())
    released = still = 0
    for a in await graph.read("alert_held", {}):
        s = await alerts.settings_for(graph, a["to"])
        if alerts.quiet_now(a["kind"], s, hour):
            still += 1
            continue
        wa = channel.whatsapp_enabled and bool(s.get("phone"))
        status, error = await alerts.deliver(
            graph,
            channel,
            s,
            a["id"],
            a["to"],
            a["title"],
            a["body"],
            json.loads(a["buttons"] or "[]"),
            a["href"] or "",
            "whatsapp" if wa else "app",
        )
        await graph.run(
            "alert_set_status", {"id": a["id"], "status": status, "error": error, "now": now}
        )
        released += 1
    return {"released": released, "still_quiet": still}
