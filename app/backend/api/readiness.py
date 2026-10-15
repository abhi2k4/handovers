"""Last-day readiness, account reassignment and backup owners: the actions that close key-person risk."""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.deps import CallerDep, GraphDep, forbid
from core.clock import OPEN, now_ms
from services import access, alerts, clearance, jobs, letters, org_policy, ramp, readiness
from services import handover as svc

router = APIRouter(prefix="/api", tags=["readiness"])


@router.get("/handovers/{hid}/readiness")
async def get_readiness(hid: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    try:
        h = await svc.get(graph, hid)
    except svc.NotFound as exc:
        raise HTTPException(404, "Not found") from exc
    forbid(access.can_view_handover(caller, h["employee_id"]), "Not part of this handover.")
    artifacts = {r["kind"] for r in await graph.read("dash_handover_artifacts", {"handover": hid})}
    plan = await ramp.get(graph, hid)
    pending = await svc.pending_followup(graph, h)
    cleared = await clearance.tally(graph, hid)
    h["approver"] = (await access.approval_routes(graph)).get(h["employee_id"])
    proposals = sum(
        1
        for x in await graph.read("reassignment_list", {"handover": hid})
        if x["status"] == "proposed"
    )
    r = readiness.build(
        h, artifacts, plan["status"] if plan else None, now_ms(), pending, cleared, proposals
    )
    reminded = {
        x["step"]: x["at"] for x in await graph.read("alert_last_reminder", {"handover": hid})
    }
    can_remind = access.can_run_handover(caller, h["employee_id"])
    r["items"] = [
        i | {"reminded_at": reminded.get(i["key"]), "remind": can_remind and not i["done"]}
        for i in r["items"]
    ]
    return readiness.for_caller(r, caller, h["employee_id"]) | {"now": now_ms()}


class ReassignIn(BaseModel):
    to: str | None = None  # defaults to the successor
    note: str = ""


async def _apply_reassignment(
    graph: GraphDep, h: dict[str, Any], aid: str, to: str, by: str
) -> dict[str, Any]:
    """Give the account's admin to `to`; the leaver keeps theirs until the last day."""
    rows = await graph.run(
        "account_reassign",
        {
            "account": aid,
            "to": to,
            "handover": h["id"],
            "now": now_ms(),
            "open": OPEN,
            "leaver_until": h["effective_at"],
        },
    )
    if not rows:
        raise HTTPException(404, "Account or person not found")
    await svc.audit(graph, h["id"], "account_reassigned", {"account": aid, "to": to}, by)
    return {"id": aid, "to": to, "status": "applied", "gaps_closed": rows[0]["gaps"]}


@router.post("/handovers/{hid}/accounts/{aid}/reassign")
async def reassign_account(
    hid: str, aid: str, body: ReassignIn, graph: GraphDep, caller: CallerDep
) -> dict[str, Any]:
    """The manager or IT proposes who takes an account; HR approves (HR has the final say, so an
    account HR hands over applies at once). Never to the leaver, or to someone leaving or gone."""
    h = await graph.one("handover_get", {"id": hid})
    if h is None:
        raise HTTPException(404, "Not found")
    forbid(
        access.can_reassign_account(caller, h["employee_id"]),
        "Only IT, HR or the leaver's manager can reassign accounts.",
    )
    if h["status"] == "cancelled":
        raise HTTPException(409, "This handover was cancelled.")
    to = body.to or h.get("successor_id")
    if not to:
        raise HTTPException(409, "Choose a successor first, or say who takes the account.")
    if to == h["employee_id"]:
        raise HTTPException(409, "The account has to go to someone other than the leaver.")
    cand = await graph.one("successor_candidate", {"id": to})
    if cand is None:
        raise HTTPException(404, "Person not found")
    if cand["status"] == "departed" or cand["leaving"]:
        raise HTTPException(409, f"{cand['name']} is leaving or has left; choose someone staying.")
    by = caller.id if caller else ""
    if caller is None or "hr" in caller.roles:
        return await _apply_reassignment(graph, h, aid, to, by)
    rid = f"rs:{uuid.uuid4().hex[:10]}"
    await graph.run(
        "reassignment_propose",
        {
            "handover": hid,
            "account": aid,
            "to": to,
            "id": rid,
            "by": caller.name,
            "now": now_ms(),
            "note": body.note,
        },
    )
    await svc.audit(graph, hid, "account_proposed", {"account": aid, "to": to}, by)
    for p in await access.hr_people(graph):
        await alerts.notify(
            graph,
            "approval",
            p["id"],
            f"Approve an account handover ({h['employee'].split(' ')[0]})",
            f"{caller.name} proposes {cand['name']} as the new admin.",
            [{"id": f"open:/handovers/{hid}?tab=clearance", "label": "Review"}],
            f"/handovers/{hid}?tab=clearance",
            hid,
        )
    return {"id": aid, "to": to, "status": "proposed", "proposal": rid}


@router.get("/handovers/{hid}/reassignments")
async def reassignments(hid: str, graph: GraphDep, caller: CallerDep) -> list[dict[str, Any]]:
    h = await graph.one("handover_get", {"id": hid})
    if h is None:
        raise HTTPException(404, "Not found")
    forbid(access.can_view_handover(caller, h["employee_id"]), "Not part of this handover.")
    return await graph.read("reassignment_list", {"handover": hid})


class DecideIn(BaseModel):
    approve: bool
    note: str = ""


@router.post("/reassignments/{rid}/decide")
async def decide_reassignment(
    rid: str, body: DecideIn, graph: GraphDep, caller: CallerDep
) -> dict[str, Any]:
    """HR approves (the account moves) or rejects a proposed account handover."""
    forbid(caller is None or "hr" in caller.roles, "Only HR approves account handovers.")
    rows = await graph.run(
        "reassignment_decide",
        {
            "id": rid,
            "status": "approved" if body.approve else "rejected",
            "by": caller.name if caller else "HR",
            "now": now_ms(),
            "note": body.note,
        },
    )
    if not rows:
        raise HTTPException(404, "No proposal waiting with that id")
    r = rows[0]
    if not body.approve:
        await svc.audit(
            graph, r["handover"], "account_rejected", {"proposal": rid}, caller.id if caller else ""
        )
        return {"id": rid, "status": "rejected"}
    h = await graph.one("handover_get", {"id": r["handover"]})
    if h is None:
        raise HTTPException(404, "Not found")
    out = await _apply_reassignment(graph, h, r["account"], r["to"], caller.id if caller else "")
    return out | {"proposal": rid}


class BackupIn(BaseModel):
    employee_id: str


@router.post("/responsibilities/{rid}/backup")
async def assign_backup(
    rid: str, body: BackupIn, graph: GraphDep, caller: CallerDep
) -> dict[str, Any]:
    now = now_ms()
    owners = [r["id"] for r in await graph.read("resp_owners", {"id": rid, "now": now})]
    if not owners:
        raise HTTPException(404, "Responsibility not found")
    forbid(
        access.can_assign_backup(caller, owners, body.employee_id),
        "Managers pick a backup from their own team; HR can pick anyone.",
    )
    if body.employee_id in owners:
        raise HTTPException(409, "Already an owner of this work.")
    rows = await graph.run(
        "resp_assign_backup",
        {
            "id": rid,
            "emp": body.employee_id,
            "now": now,
            "open": OPEN,
            "by": caller.id if caller else "system",
        },
    )
    if not rows:
        raise HTTPException(404, "Backup must be an active employee")
    return rows[0]


@router.get("/handovers/{hid}/clearance")
async def get_clearance(hid: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    try:
        h = await svc.get(graph, hid)
    except svc.NotFound as exc:
        raise HTTPException(404, "Not found") from exc
    forbid(access.can_view_handover(caller, h["employee_id"]), "Not part of this handover.")
    items = await clearance.load(graph, hid)
    if not items:  # handovers opened before clearance existed
        await clearance.ensure(graph, hid, h["employee_id"])
        items = await clearance.load(graph, hid)
    confirmed, total = clearance.counts(items)
    complete = total > 0 and confirmed == total
    p = await org_policy.load(graph)
    gate = letters.gate(h, complete, p, now_ms())
    is_hr = caller is None or "hr" in caller.roles
    ready = complete and h["status"] == "transferred"
    # HR prepares the letter once it is ready; everyone else sees it only after it is sent.
    letter = await letters.build(graph, h) if (ready and is_hr) or h.get("letter_sent_at") else None
    scheduled = next(
        (
            j
            for j in await graph.read("job_list", {"limit": 500})
            if j["key"] == f"letter:{hid}" and j["status"] == "queued"
        ),
        None,
    )
    return {
        "items": items,
        "confirmed": confirmed,
        "total": total,
        "complete": complete,
        "can_confirm": is_hr,
        "can_mark": access.can_run_handover(caller, h["employee_id"])
        or access.can_reassign_account(caller, h["employee_id"]),
        # The letter says the handover is done, so it needs the approved transfer too.
        "transferred": h["status"] == "transferred",
        "letter": letter,
        "letter_gate": gate,
        "letter_sent_at": h.get("letter_sent_at"),
        "letter_scheduled_at": scheduled["run_at"] if scheduled else None,
        "email_draft": letters.email_draft(letter, h.get("employee_email"))
        if letter and is_hr and not h.get("letter_sent_at")
        else None,
        "proposals": [
            x
            for x in await graph.read("reassignment_list", {"handover": hid})
            if x["status"] == "proposed"
        ],
    }


class ClearIn(BaseModel):
    key: str
    status: str


@router.post("/handovers/{hid}/clearance")
async def set_clearance(
    hid: str, body: ClearIn, graph: GraphDep, caller: CallerDep
) -> dict[str, Any]:
    h = await graph.one("handover_get", {"id": hid})
    if h is None:
        raise HTTPException(404, "Not found")
    if body.status not in clearance.STATUSES:
        raise HTTPException(422, "Unknown status")
    is_hr = caller is None or "hr" in caller.roles
    current = next((i for i in await clearance.load(graph, hid) if i["key"] == body.key), None)
    if current is None:
        raise HTTPException(404, "No such clearance row")
    if body.status == "confirmed":
        forbid(is_hr, "Only HR confirms clearance.")
        if current["status"] != "done":
            # Two sign-offs: the row's owner marks it done, then HR confirms.
            raise HTTPException(409, f"{current['owner']} marks this done first; then HR confirms.")
    else:
        forbid(
            access.can_run_handover(caller, h["employee_id"])
            or access.can_reassign_account(caller, h["employee_id"]),
            "Only HR, IT or the manager can change clearance.",
        )
        if current["status"] == "confirmed":
            # HR has the final say: a confirmed row changes only by HR.
            forbid(is_hr, "Only HR can reopen a row HR confirmed.")
    rows = await graph.run(
        "clearance_set",
        {
            "handover": hid,
            "key": body.key,
            "status": body.status,
            "by": caller.name if caller else "",
            "now": now_ms(),
        },
    )
    if not rows:
        raise HTTPException(404, "No such clearance row")
    return await get_clearance(hid, graph, caller)


class LetterIn(BaseModel):
    subject: str = ""
    body: str = ""
    when: str = "now"  # now | last_day


@router.post("/handovers/{hid}/letter")
async def send_letter(
    hid: str, body: LetterIn, graph: GraphDep, caller: CallerDep
) -> dict[str, Any]:
    """HR sends the relieving letter by email now, or schedules it for the last day."""
    forbid(caller is None or "hr" in caller.roles, "Only HR sends the relieving letter.")
    by = caller.name if caller else "HR"
    if body.when == "last_day":
        h = await graph.one("handover_get", {"id": hid})
        if h is None:
            raise HTTPException(404, "Not found")
        await jobs.enqueue(
            graph,
            "letter",
            max(h["effective_at"], now_ms()),
            f"letter:{hid}",
            {"by": by, "subject": body.subject, "body": body.body},
            hid,
        )
        await svc.audit(graph, hid, "letter.scheduled", {"at": h["effective_at"]}, by)
        return {"scheduled": True, "at": h["effective_at"]}
    try:
        return await letters.send(graph, hid, by, {"subject": body.subject, "body": body.body})
    except (svc.NotFound, svc.Conflict) as exc:
        raise HTTPException(409, str(exc)) from exc
