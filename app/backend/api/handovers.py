"""Handovers: open, outputs, exit interview, transfer."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from api.deps import CallerDep, GraphDep, LLMDep, forbid
from core.clock import DAY_MS, now_ms
from core.graph import Graph
from ingestion.pipeline import to_markdown
from services import access, alerts, generators, handover_rules, org_policy
from services import handover as svc

router = APIRouter(prefix="/api", tags=["handovers"])


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, svc.NotFound):
        return HTTPException(404, "Not found")
    if isinstance(exc, svc.NeedsConfirmation):
        # The UI shows the message and asks; sending `confirmed: true` goes ahead.
        return HTTPException(409, {"code": exc.code, "message": str(exc), "confirm": True})
    if isinstance(exc, svc.Conflict):
        return HTTPException(409, str(exc))
    raise exc


async def _leaver(graph: GraphDep, hid: str) -> str:
    row = await graph.one("handover_get", {"id": hid})
    if row is None:
        raise HTTPException(404, "Not found")
    leaver: str = row["employee_id"]
    return leaver


async def _gap_leaver(graph: GraphDep, gid: str) -> str:
    row = await graph.one("gap_get", {"id": gid})
    if row is None:
        raise HTTPException(404, "Not found")
    leaver: str = row["employee_id"]
    return leaver


RUN = "Only HR or the leaver's manager can do this."
READ = "Only the leaver and their manager can read this."
PART = "Not part of this handover."
ANSWER = "Only the leaver answers these questions."
APPROVE = (
    "Only the approver can do this: the leaver's manager, or the next one up if they are away."
)


class OpenIn(BaseModel):
    employee_id: str
    successor_id: str | None = None
    notice_days: int = Field(default=30, ge=0, le=365)
    confirmed: bool = False  # yes, a successor from another team


@router.get("/handovers")
async def list_handovers(graph: GraphDep, caller: CallerDep) -> list[dict[str, Any]]:
    rows = await graph.read("handover_list", {})
    if caller is None or access.can_view_org(caller):
        return rows
    mine = set(caller.leaving) | set(caller.managing)
    approves = caller.approves or frozenset()
    return [h for h in rows if h["id"] in mine or h["employee_id"] in approves]


@router.post("/handovers", status_code=201)
async def open_handover(body: OpenIn, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    forbid(access.can_run_handover(caller, body.employee_id), RUN)
    try:
        hid = await svc.open_handover(
            graph,
            body.employee_id,
            body.successor_id,
            body.notice_days,
            caller.id if caller else "",
            body.confirmed,
        )
    except (svc.NotFound, svc.Conflict) as exc:
        raise _http(exc) from exc
    h = await svc.get(graph, hid)
    await _announce(graph, h, caller)
    return h


async def _announce(graph: Graph, h: dict[str, Any], caller: access.Caller | None) -> None:
    """Tell HR and the leaver's manager the moment someone resigns: the handover clock starts now."""
    days = max(0, round((h["effective_at"] - now_ms()) / DAY_MS))
    at_risk = sum(1 for g in h["gaps"] if g["status"] == "open")
    first = h["employee"].split(" ")[0]
    hr = [p["id"] for p in await access.hr_people(graph)]
    recipients = alerts.resignation_recipients(
        hr, h.get("manager_id"), caller.id if caller else None
    )
    for emp, is_manager in recipients:
        lead = f"{first} reports to you" if is_manager else h["title"]
        ask = " You choose the successor and approve the transfer." if is_manager else ""
        await alerts.notify(
            graph,
            "resignation",
            emp,
            f"{h['employee']} is leaving",
            f"{lead} · last day {alerts.days_text(days)}. {at_risk} things only {first} holds.{ask}",
            [{"id": f"open:/handovers/{h['id']}", "label": "Open handover"}],
            f"/handovers/{h['id']}",
            h["id"],
        )


@router.get("/handovers/{hid}")
async def get_handover(hid: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    try:
        h = await svc.get(graph, hid)
    except svc.NotFound as exc:
        raise _http(exc) from exc
    forbid(access.can_view_handover(caller, h["employee_id"]), PART)
    p = await org_policy.load(graph)
    routes = await access.approval_routes(graph)
    leaver = h["employee_id"]
    h = h | {
        "approver": routes.get(leaver) or access.pick_approver([]),
        "cancel": handover_rules.cancel_window(h, p, now_ms()),
        "can": {
            "run": access.can_run_handover(caller, leaver),
            "approve": access.can_approve(caller, leaver),
            "ask": access.can_ask_question(caller, leaver),
            "dismiss": access.can_dismiss_question(caller, leaver, False),
            "answer": access.can_answer(caller, leaver),
            "notes": access.can_run_handover(caller, leaver) or access.can_approve(caller, leaver),
        },
    }
    if not access.can_read_answers(caller, leaver):
        h = {**h, "gaps": access.redact_gaps(h["gaps"]), "redacted": True}
    return h


class SuccessorIn(BaseModel):
    successor_id: str
    confirmed: bool = False


@router.post("/handovers/{hid}/successor")
async def set_successor(
    hid: str, body: SuccessorIn, graph: GraphDep, caller: CallerDep
) -> dict[str, Any]:
    forbid(access.can_run_handover(caller, await _leaver(graph, hid)), RUN)
    try:
        await svc.set_successor(
            graph, hid, body.successor_id, body.confirmed, caller.id if caller else ""
        )
    except (svc.NotFound, svc.Conflict) as exc:
        raise _http(exc) from exc
    return await svc.get(graph, hid)


@router.post("/handovers/{hid}/analyze")
async def analyze(hid: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    forbid(access.can_run_handover(caller, await _leaver(graph, hid)), RUN)
    try:
        await svc.analyze(graph, hid)
        return await svc.get(graph, hid)
    except svc.NotFound as exc:
        raise _http(exc) from exc


@router.get("/handovers/{hid}/artifacts/{kind}")
async def artifact(
    hid: str, kind: str, graph: GraphDep, llm: LLMDep, caller: CallerDep, refresh: bool = False
) -> dict[str, Any]:
    forbid(access.can_run_handover(caller, await _leaver(graph, hid)), RUN)
    try:
        return await svc.artifact(graph, llm, hid, kind, refresh)
    except svc.NotFound as exc:
        raise _http(exc) from exc


@router.post("/handovers/{hid}/resume-check")
async def resume_check(
    hid: str,
    graph: GraphDep,
    llm: LLMDep,
    caller: CallerDep,
    text: Annotated[str, Form()] = "",
    file: Annotated[UploadFile | None, File()] = None,
) -> dict[str, Any]:
    forbid(access.can_run_handover(caller, await _leaver(graph, hid)), RUN)
    if file is not None:
        text = to_markdown(file.filename or "resume.pdf", await file.read())
    if not text.strip():
        raise HTTPException(422, "Paste the resume text or attach a file.")
    try:
        h = await svc.get(graph, hid)
    except svc.NotFound as exc:
        raise _http(exc) from exc
    return await generators.check_resume(graph, llm, h["employee_id"], text)


@router.get("/handovers/{hid}/interview")
async def interview(hid: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    try:
        h = await svc.get(graph, hid)
    except svc.NotFound as exc:
        raise _http(exc) from exc
    forbid(access.can_view_handover(caller, h["employee_id"]), PART)
    questions, extra = handover_rules.interview_sets(h["gaps"])
    if not access.can_read_answers(caller, h["employee_id"]):
        questions, extra = access.redact_gaps(questions), access.redact_gaps(extra)
    return {
        "employee": h["employee"],
        "questions": questions,
        "extra": extra,
        "answered": sum(1 for q in questions if q["status"] == "answered"),
    }


class QuestionIn(BaseModel):
    question: str = Field(min_length=8, max_length=600)
    follows: str | None = None  # the question this one follows up on


@router.post("/handovers/{hid}/questions", status_code=201)
async def add_question(
    hid: str, body: QuestionIn, graph: GraphDep, caller: CallerDep
) -> dict[str, Any]:
    """HR or the manager asks the leaver something more, or follows up on an answer."""
    leaver = await _leaver(graph, hid)
    forbid(access.can_ask_question(caller, leaver), "Only HR or the manager can add questions.")
    try:
        gid = await svc.add_question(
            graph, hid, body.question, caller.id if caller else "", body.follows
        )
    except (svc.NotFound, svc.Conflict) as exc:
        raise _http(exc) from exc
    await alerts.notify(
        graph,
        "reminder",
        leaver,
        "A new exit-interview question",
        f"{caller.name if caller else 'HR'} asked: {body.question[:140]}",
        [{"id": f"open:/handovers/{hid}?tab=interview", "label": "Answer"}],
        f"/handovers/{hid}?tab=interview",
        hid,
    )
    return {"id": gid}


class AnswerIn(BaseModel):
    answer: str = Field(min_length=3)


class ConfirmIn(AnswerIn):
    facts: list[dict[str, Any]] = Field(default_factory=list)
    # "Sources disagree": the claim the leaver named as current; "" = neither (both stay open).
    keep: str | None = None


@router.post("/gaps/{gid}/preview")
async def preview(
    gid: str, body: AnswerIn, graph: GraphDep, llm: LLMDep, caller: CallerDep
) -> dict[str, Any]:
    forbid(access.can_answer(caller, await _gap_leaver(graph, gid)), ANSWER)
    try:
        return await svc.preview_answer(graph, llm, gid, body.answer)
    except svc.NotFound as exc:
        raise _http(exc) from exc


@router.post("/gaps/{gid}/confirm")
async def confirm(gid: str, body: ConfirmIn, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    forbid(access.can_answer(caller, await _gap_leaver(graph, gid)), ANSWER)
    try:
        return await svc.confirm_answer(graph, gid, body.answer, body.facts, body.keep)
    except svc.NotFound as exc:
        raise _http(exc) from exc


class DismissIn(BaseModel):
    reason: str = ""


@router.post("/gaps/{gid}/dismiss")
async def dismiss(
    gid: str, graph: GraphDep, caller: CallerDep, body: DismissIn | None = None
) -> dict[str, str]:
    gap = await graph.one("gap_get", {"id": gid})
    if gap is None:
        raise HTTPException(404, "Not found")
    forbid(
        access.can_dismiss_question(
            caller, gap["employee_id"], gap["rule"] == handover_rules.MANDATORY
        ),
        "Only the leaver's manager can drop a question, and never one the policy requires.",
    )
    try:
        await svc.dismiss_gap(graph, gid, caller.id if caller else "", (body or DismissIn()).reason)
    except (svc.NotFound, svc.Conflict) as exc:
        raise _http(exc) from exc
    return {"id": gid, "status": "dismissed"}


@router.get("/handovers/{hid}/transfer")
async def transfer_preview(hid: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    leaver = await _leaver(graph, hid)
    forbid(access.can_read_answers(caller, leaver), READ)
    try:
        preview = await svc.transfer_preview(graph, hid)
    except svc.NotFound as exc:
        raise _http(exc) from exc
    if caller is not None and caller.id != leaver:
        return access.redact_excluded(preview)
    return preview


class ApproveIn(BaseModel):
    approved_by: str
    comment: str = ""


@router.post("/handovers/{hid}/transfer")
async def approve(hid: str, body: ApproveIn, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    forbid(access.can_approve(caller, await _leaver(graph, hid)), APPROVE)
    approver = caller.id if caller else body.approved_by
    try:
        return await svc.approve_and_transfer(graph, hid, approver, body.comment)
    except (svc.NotFound, svc.Conflict) as exc:
        raise _http(exc) from exc


@router.get("/handovers/{hid}/audit")
async def audit(hid: str, graph: GraphDep, caller: CallerDep) -> list[dict[str, Any]]:
    forbid(access.can_run_handover(caller, await _leaver(graph, hid)), RUN)
    return await graph.read("audit_list", {"handover": hid})


class RejectIn(BaseModel):
    comment: str = Field(min_length=5, max_length=1000)


@router.post("/handovers/{hid}/transfer/reject")
async def reject(hid: str, body: RejectIn, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    """The approver sends the transfer back with what to fix. HR and the leaver are told."""
    leaver = await _leaver(graph, hid)
    forbid(access.can_approve(caller, leaver), APPROVE)
    by = caller.id if caller else (await access.approval_routes(graph)).get(leaver, {}).get("id")
    if not by:
        raise HTTPException(400, "Choose who you are (View as) to reject.")
    try:
        out = await svc.reject_transfer(graph, hid, by, body.comment)
    except (svc.NotFound, svc.Conflict) as exc:
        raise _http(exc) from exc
    h = await svc.get(graph, hid)
    for to in [leaver, *[p["id"] for p in await access.hr_people(graph)]]:
        await alerts.notify(
            graph,
            "approval",
            to,
            f"{h['employee'].split(' ')[0]}'s transfer was sent back",
            f"{caller.name if caller else 'The approver'}: {body.comment[:160]}",
            [{"id": f"open:/handovers/{hid}?tab=transfer", "label": "Open"}],
            f"/handovers/{hid}?tab=transfer",
            hid,
        )
    return out


class CancelIn(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


@router.post("/handovers/{hid}/cancel")
async def cancel(hid: str, body: CancelIn, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    """A withdrawn resignation, within the company's withdrawal window: HR or the manager."""
    leaver = await _leaver(graph, hid)
    forbid(access.can_run_handover(caller, leaver), RUN)
    try:
        out = await svc.cancel(graph, hid, caller.id if caller else "", body.reason)
    except (svc.NotFound, svc.Conflict) as exc:
        raise _http(exc) from exc
    h = await svc.get(graph, hid)
    told = {leaver, h.get("manager_id"), h.get("successor_id")} - {
        None,
        caller.id if caller else None,
    }
    for to in told:
        await alerts.notify(
            graph,
            "reminder",
            str(to),
            f"{h['employee']}'s handover was cancelled",
            f"Reason: {body.reason[:160]}",
            [{"id": f"open:/handovers/{hid}", "label": "Open"}],
            f"/handovers/{hid}",
            hid,
        )
    return out


@router.get("/handovers/{hid}/capture-plan")
async def capture_plan(hid: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    """The days left, day by day: what to capture from the leaver, and when."""
    try:
        h = await svc.get(graph, hid)
    except svc.NotFound as exc:
        raise _http(exc) from exc
    forbid(access.can_view_handover(caller, h["employee_id"]), PART)
    return await svc.capture_plan(graph, h, access.can_read_answers(caller, h["employee_id"]))


class NoteIn(BaseModel):
    text: str = Field(min_length=2, max_length=1000)
    kind: str = "note"  # note | confirmation


@router.get("/handovers/{hid}/notes")
async def notes(hid: str, graph: GraphDep, caller: CallerDep) -> list[dict[str, Any]]:
    leaver = await _leaver(graph, hid)
    forbid(access.can_run_handover(caller, leaver) or access.can_approve(caller, leaver), RUN)
    return await graph.read("note_list", {"handover": hid})


@router.post("/handovers/{hid}/notes", status_code=201)
async def add_note(hid: str, body: NoteIn, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    """HR's notes and confirmations on a handover (also the approver's). Not shown to the leaver."""
    leaver = await _leaver(graph, hid)
    forbid(access.can_run_handover(caller, leaver) or access.can_approve(caller, leaver), RUN)
    if body.kind not in ("note", "confirmation"):
        raise HTTPException(422, "A note or a confirmation.")
    nid = f"note:{uuid.uuid4().hex[:10]}"
    await graph.run(
        "note_add",
        {
            "handover": hid,
            "id": nid,
            "kind": body.kind,
            "text": body.text.strip(),
            "by": caller.id if caller else "",
            "by_name": caller.name if caller else "HR",
            "now": now_ms(),
        },
    )
    await svc.audit(graph, hid, f"note.{body.kind}", {"note": nid}, caller.id if caller else "")
    return {"id": nid}
