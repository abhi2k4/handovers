"""Alerts: settings, the in-app inbox, reminders, the daily digest and the WhatsApp webhook."""

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from api.deps import CallerDep, GraphDep, forbid
from core.clock import DAY_MS, now_ms
from core.config import get_settings
from core.graph import Graph
from services import (
    access,
    alerts,
    clearance,
    delivery,
    notices,
    org_policy,
    ramp,
    readiness,
    whatsapp,
)
from services import handover as svc

router = APIRouter(prefix="/api", tags=["alerts"])


def _me(caller: access.Caller | None) -> str:
    if caller is None:
        raise HTTPException(400, "Choose who you are (View as) to manage alerts.")
    return caller.id


class SettingsIn(BaseModel):
    phone: str = ""
    email: bool = True  # also email this person's alerts, when the email channel is on
    modes: dict[str, str] = {}
    quiet_from: int = alerts.QUIET[0]
    quiet_to: int = alerts.QUIET[1]


@router.get("/alerts/settings")
async def get_settings_(graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    s = await alerts.settings_for(graph, _me(caller))
    kinds = [{"key": k, "label": v["label"]} for k, v in alerts.KINDS.items()]
    channel = await delivery.effective(graph, get_settings())
    address = (await graph.one("employee_email", {"emp": _me(caller)}) or {}).get("email")
    return s | {
        "kinds": kinds,
        "whatsapp": channel.whatsapp_enabled,
        # The email channel is on, and where this person's alerts would go.
        "email_channel": channel.email_enabled,
        "email_address": address or "",
    }


@router.put("/alerts/settings")
async def put_settings(body: SettingsIn, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    emp = _me(caller)
    # A local number gets the organisation's country code (policy), not an assumed +91.
    phone = org_policy.phone(await org_policy.load(graph), body.phone)
    bad = {m for m in body.modes.values() if m not in alerts.MODES}
    if bad or not (0 <= body.quiet_from < 24 and 0 <= body.quiet_to < 24):
        raise HTTPException(422, "Unknown alert mode or hour.")
    await alerts.save_settings(graph, emp, body.model_dump() | {"phone": phone})
    return await get_settings_(graph, caller)


@router.get("/alerts")
async def inbox(graph: GraphDep, caller: CallerDep) -> list[dict[str, Any]]:
    rows = await graph.read("alert_list", {"to": _me(caller)})
    return [r | {"buttons": json.loads(r["buttons"] or "[]")} for r in rows]


@router.post("/alerts/test")
async def test(graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    return await alerts.notify(
        graph,
        "reminder",
        _me(caller),
        "Alerts are on",
        "This is how Handovers reaches you. Reply buttons work right here.",
        [{"id": "open:/alerts", "label": "Open settings"}],
        href="/alerts",
    )


class RemindIn(BaseModel):
    step: str


async def _recipients(graph: Graph, key: str, h: dict[str, Any]) -> list[str]:
    if key in {"interview"}:
        return [h["employee_id"]]
    if key in {"ramp", "transfer"}:
        # The approver: the manager, or the next one up when the manager is away; else HR.
        approver = (await access.approval_routes(graph)).get(h["employee_id"], {}).get("id")
        if approver:
            return [approver]
    rows = await access.hr_people(graph)
    return [r["id"] for r in rows]


@router.post("/handovers/{hid}/remind")
async def remind(hid: str, body: RemindIn, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    try:
        h = await svc.get(graph, hid)
    except svc.NotFound as exc:
        raise HTTPException(404, "Not found") from exc
    forbid(access.can_run_handover(caller, h["employee_id"]), "Only HR or the manager can remind.")
    artifacts = {r["kind"] for r in await graph.read("dash_handover_artifacts", {"handover": hid})}
    plan = await ramp.get(graph, hid)
    cleared = await clearance.tally(graph, hid)
    r = readiness.build(h, artifacts, plan["status"] if plan else None, now_ms(), 0, cleared)
    item = next((i for i in r["items"] if i["key"] == body.step), None)
    if item is None or item["done"]:
        raise HTTPException(409, "Nothing to remind about.")
    by = caller.name.split(" ")[0] if caller else "HR"
    msg = alerts.reminder(item, h, by, r["days_left"])
    sent = [
        await alerts.notify(
            graph,
            msg["kind"],
            to,
            msg["title"],
            msg["body"],
            msg["buttons"],
            item["href"],
            hid,
            body.step,
        )
        for to in await _recipients(graph, body.step, h)
        if not caller or to != caller.id
    ]
    if not sent:
        raise HTTPException(409, "Nobody else to remind for this step.")
    return {"step": body.step, "sent": sent, "at": now_ms()}


class ActIn(BaseModel):
    button: str


async def act(graph: Graph, aid: str, button: str, actor: access.Caller | None) -> dict[str, Any]:
    """Run what an alert button asks for, as the person the alert was sent to."""
    a = await graph.one("alert_get", {"id": aid})
    if a is None:
        raise HTTPException(404, "Alert not found")
    if actor is not None and actor.id != a["to"]:
        raise HTTPException(403, "This alert was sent to someone else.")
    action, _, arg = button.partition(":")
    result: dict[str, Any] = {"action": action}
    if action == "open":
        result["href"] = arg
    elif action == "approve":
        h = await svc.get(graph, arg)
        forbid(
            access.can_approve(actor, h["employee_id"]), "Only the leaver's manager can approve."
        )
        approver = actor.id if actor else a["to"]
        try:
            await svc.approve_and_transfer(graph, arg, approver, "Approved from an alert")
        except svc.Conflict as exc:
            raise HTTPException(409, str(exc)) from exc
        result["href"] = f"/handovers/{arg}?tab=transfer"
    elif action == "snooze":
        result["until"] = now_ms() + DAY_MS
    else:
        raise HTTPException(422, "Unknown button")
    await graph.run("alert_act", {"id": aid, "acted": button, "now": now_ms()})
    return result


@router.post("/alerts/{aid}/act")
async def act_in_app(aid: str, body: ActIn, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    return await act(graph, aid, body.button, caller)


@router.post("/alerts/digest")
async def digest(graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    """Send today's summary and last-day warnings now. The job queue does this every morning at
    the policy's digest hour (services/jobs.py); HR can also send it by hand."""
    forbid(caller is None or "hr" in caller.roles, "Only HR sends the digest.")
    return {"sent": [*await notices.send_digest(graph), *await notices.lastday_alerts(graph)]}


CHANNEL_ADMIN = "Only the signed-in platform admin sets up alert delivery."


@router.get("/alerts/delivery/{channel}")
async def delivery_settings(channel: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    """One channel (whatsapp, email) for the platform admin: switch, settings (masked), setup."""
    forbid(access.can_view_setup(caller), CHANNEL_ADMIN)
    try:
        return await delivery.describe(graph, get_settings(), channel)
    except delivery.InvalidChannel as exc:
        raise HTTPException(404, str(exc)) from exc


class DeliveryIn(BaseModel):
    values: dict[str, str] | None = None  # a blank secret keeps the stored one
    enabled: bool | None = None  # the master switch: off, nobody gets this channel


@router.put("/alerts/delivery/{channel}")
async def save_delivery(
    channel: str, body: DeliveryIn, graph: GraphDep, caller: CallerDep
) -> dict[str, Any]:
    forbid(access.can_configure(caller), CHANNEL_ADMIN)
    by = caller.id if caller else "system"
    try:
        if body.values is not None:
            await delivery.save(graph, channel, body.values, by)
        if body.enabled is not None:
            await delivery.set_enabled(graph, channel, body.enabled, by)
        return await delivery.describe(graph, get_settings(), channel)
    except delivery.InvalidChannel as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/alerts/delivery/{channel}/test")
async def test_delivery(channel: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    """WhatsApp: ask Meta for the phone number (sends nothing). Email: one to the From address."""
    forbid(access.can_configure(caller), CHANNEL_ADMIN)
    try:
        return await delivery.test(graph, get_settings(), channel)
    except delivery.InvalidChannel as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/whatsapp/webhook", response_class=PlainTextResponse)
async def verify(
    graph: GraphDep,
    mode: str = Query("", alias="hub.mode"),
    token: str = Query("", alias="hub.verify_token"),
    challenge: str = Query("", alias="hub.challenge"),
) -> str:
    s = await delivery.effective(graph, get_settings())
    if mode != "subscribe" or not s.whatsapp_verify_token or token != s.whatsapp_verify_token:
        raise HTTPException(403, "Verification failed")
    return challenge


@router.post("/whatsapp/webhook")
async def webhook(request: Request, graph: GraphDep) -> dict[str, Any]:
    """Reply-button taps from WhatsApp: run the action as the person the alert went to."""
    done = []
    for phone, button_id in whatsapp.button_reply(await request.json()):
        aid, _, button = button_id.partition("|")
        a = await graph.one("alert_get", {"id": aid})
        if a is None:
            continue
        s = await alerts.settings_for(graph, a["to"])
        if s["phone"] != phone:
            continue  # only the recipient's own number can act
        try:
            done.append(await act(graph, aid, button, await access.load_caller(graph, a["to"])))
        except HTTPException as exc:
            done.append({"error": exc.detail})
    return {"handled": done}
