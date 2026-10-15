"""Handover workflow: open, analyse, exit interview, approve, transfer.

States: pending -> interview -> transferred, or cancelled (a withdrawn resignation, within the
policy's window). Every transition is a graph write plus an AuditEvent. Humans gate the steps that
matter: the leaver confirms what gets recorded from their answers, the approver (the manager, or
the next one up) approves or rejects what moves to the successor, and HR signs the exit off.
Approving the transfer does not end the leaver's time: they keep access and can still answer
until the last day, when the `depart` job marks them as left.
"""

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from core.clock import iso, now_ms
from core.graph import Graph
from core.llm import LLM, LLMUnavailable
from ingestion.schema import Fact, SourceIn
from ingestion.writer import recompute_confidence, write_source
from services import analysis, clearance, generators, handover_rules, org_policy, policy


class Conflict(Exception):
    pass


class NeedsConfirmation(Conflict):
    """Allowed, but the person choosing must confirm first (e.g. a successor from another team)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class NotFound(Exception):
    pass


def _id(prefix: str) -> str:
    return f"{prefix}:{uuid.uuid4().hex[:10]}"


async def audit(
    graph: Graph, handover: str | None, type_: str, payload: dict[str, Any], actor: str = ""
) -> None:
    await graph.run(
        "audit_add",
        {
            "id": _id("evt"),
            "type": type_,
            "now": now_ms(),
            "payload": json.dumps(payload),
            "actor": actor,
            "handover": handover or "",
        },
    )


# ---- lifecycle -----------------------------------------------------------------------------------


async def check_successor(graph: Graph, leaver: str, successor: str, confirmed: bool) -> None:
    """Refuse a successor who cannot take over (the leaver, someone leaving, someone gone); ask
    for confirmation when they are from another team."""
    me = await graph.one("successor_candidate", {"id": leaver})
    cand = await graph.one("successor_candidate", {"id": successor})
    problem = handover_rules.successor_problem(me or {"id": leaver}, cand)
    if problem and problem["blocking"]:
        raise Conflict(problem["message"])
    if problem and not confirmed:
        raise NeedsConfirmation(problem["code"], problem["message"])


async def ensure_mandatory(graph: Graph, hid: str, p: dict[str, Any] | None = None) -> int:
    """The policy's questions for every leaver, added once per handover (idempotent)."""
    p = p or await org_policy.load(graph)
    now = now_ms()
    for i, q in enumerate(p["mandatory_questions"]):
        await graph.run(
            "gap_add_question",
            {
                "handover": hid,
                "id": f"{hid}:M:{i}",
                "rule": handover_rules.MANDATORY,
                "target": f"{hid}:M:{i}",
                "title": q,
                "question": q,
                "priority": 0.97,
                "now": now,
                "context": "",
                "by": "policy",
            },
        )
    return len(p["mandatory_questions"])


async def open_handover(
    graph: Graph,
    emp: str,
    successor: str | None,
    notice_days: int,
    actor: str = "",
    confirmed: bool = False,
) -> str:
    if await graph.read("handover_open_for_employee", {"emp": emp}):
        raise Conflict("This person already has an open handover.")
    if successor:
        await check_successor(graph, emp, successor, confirmed)
    now = now_ms()
    hid = _id("ho")
    rows = await graph.run(
        "handover_create",
        {
            "emp": emp,
            "id": hid,
            "trigger": "resignation",
            "now": now,
            "effective_at": now + notice_days * 86_400_000,
            "notice_days": notice_days,
        },
    )
    if not rows:
        raise NotFound(emp)
    if successor:
        await graph.run("handover_set_successor", {"id": hid, "successor": successor})
    await audit(graph, hid, "handover.opened", {"employee": emp, "notice_days": notice_days}, actor)
    await ensure_mandatory(graph, hid)
    await analyze(graph, hid)
    await clearance.ensure(graph, hid, emp)
    from services import jobs

    # The last day: mark the leaver as left and end their access, on time, without anyone clicking.
    await jobs.enqueue(
        graph, "depart", now + notice_days * 86_400_000, f"depart:{hid}", handover=hid
    )
    return hid


async def get(graph: Graph, hid: str) -> dict[str, Any]:
    h = await graph.one("handover_get", {"id": hid})
    if not h:
        raise NotFound(hid)
    gaps = await graph.read("gap_list", {"handover": hid})
    core, extra = handover_rules.interview_sets(gaps)
    core_ids, extra_ids = {g["id"] for g in core}, {g["id"] for g in extra}
    for g in gaps:
        g["label"] = policy.RULE_LABEL.get(g["rule"], g["rule"])
        # `interview`: one of the questions readiness waits on; `extra`: more, for the days left.
        g["interview"] = g["id"] in core_ids
        g["extra"] = g["id"] in extra_ids
        g["mandatory"] = g["rule"] == handover_rules.MANDATORY
    transfer = await graph.one("transfer_for_handover", {"handover": hid})
    return {**h, "gaps": gaps, "transfer": transfer, "effective_iso": iso(h.get("effective_at"))}


async def set_successor(
    graph: Graph, hid: str, successor: str, confirmed: bool = False, actor: str = ""
) -> None:
    h = await graph.one("handover_get", {"id": hid})
    if not h:
        raise NotFound(hid)
    if h["status"] == "cancelled":
        raise Conflict("This handover was cancelled.")
    await check_successor(graph, h["employee_id"], successor, confirmed)
    await graph.run("handover_set_successor", {"id": hid, "successor": successor})
    await audit(
        graph, hid, "handover.successor", {"successor": successor, "confirmed": confirmed}, actor
    )


async def analyze(graph: Graph, hid: str) -> int:
    h = await graph.one("handover_get", {"id": hid})
    if not h:
        raise NotFound(hid)
    seeds = await analysis.find_gaps(graph, h["employee_id"])
    now = now_ms()
    for s in seeds:
        await graph.run(
            "gap_upsert",
            {
                "handover": hid,
                "id": f"{hid}:{s.rule}:{s.target}",
                "rule": s.rule,
                "target": s.target,
                "target_kind": s.target_kind,
                "title": s.title,
                "seed": s.question,
                "question": s.question,
                "priority": s.priority,
                "now": now,
                "context": s.context,
            },
        )
    if h["status"] == "pending":
        await graph.run("handover_set_status", {"id": hid, "status": "interview", "now": now})
    await audit(graph, hid, "handover.analyzed", {"gaps": len(seeds)})
    return len(seeds)


# ---- artifacts -----------------------------------------------------------------------------------

ARTIFACT_KINDS = ("jd", "screening", "interview-kit", "plan")


async def artifact(
    graph: Graph, llm: LLM, hid: str, kind: str, refresh: bool = False
) -> dict[str, Any]:
    if kind not in ARTIFACT_KINDS:
        raise NotFound(kind)
    h = await get(graph, hid)
    if not refresh and kind != "plan":
        cached = await graph.one("artifact_get", {"handover": hid, "kind": kind})
        if cached and cached.get("content"):
            return {
                **json.loads(cached["content"]),
                "updated_at": cached["updated_at"],
                "model": cached["model"],
            }
    emp = h["employee_id"]
    if kind == "jd":
        content = await generators.build_jd(graph, llm, emp)
    elif kind == "screening":
        content = await generators.build_screening(graph, llm, emp)
    elif kind == "interview-kit":
        content = await generators.build_interview_kit(graph, llm, emp)
    else:
        successor = (
            {"id": h["successor_id"], "name": h["successor"]} if h.get("successor_id") else None
        )
        content = await generators.build_plan(graph, emp, successor, h["gaps"])
    now = now_ms()
    model = str(content.get("phrased_by") or ("rules" if kind == "plan" else llm.model))
    await graph.run(
        "artifact_upsert",
        {
            "handover": hid,
            "id": f"{hid}:{kind}",
            "kind": kind,
            "content": json.dumps(content),
            "now": now,
            "model": model,
        },
    )
    return {**content, "updated_at": now, "model": model}


# ---- exit interview ------------------------------------------------------------------------------


def interview_questions(
    gaps: list[dict[str, Any]], limit: int = policy.INTERVIEW_SIZE
) -> list[dict[str, Any]]:
    """The questions readiness waits on (mandatory, asked, and the top ones the graph found)."""
    return handover_rules.interview_sets(gaps, limit)[0]


async def add_question(
    graph: Graph, hid: str, question: str, by: str, follows: str | None = None
) -> str:
    """HR or the manager asks the leaver something more, or follows up on an answer."""
    h = await graph.one("handover_get", {"id": hid})
    if not h:
        raise NotFound(hid)
    if h["status"] == "cancelled":
        raise Conflict("This handover was cancelled.")
    if (h.get("employee_status") or "") == "departed":
        raise Conflict(f"{h['employee']} has already left.")
    gid = f"{hid}:Q:{uuid.uuid4().hex[:8]}"
    text = question.strip()
    await graph.run(
        "gap_add_question",
        {
            "handover": hid,
            "id": gid,
            "rule": handover_rules.ASKED,
            "target": follows or gid,
            "title": text if len(text) <= 90 else text[:87].rstrip() + "...",
            "question": text,
            "priority": 0.96,
            "now": now_ms(),
            "context": follows or "",
            "by": by,
        },
    )
    await audit(graph, hid, "interview.asked", {"gap": gid, "follows": follows}, by)
    return gid


def _steps(answer: str) -> list[str]:
    body = answer.split(":", 1)[1] if "steps:" in answer.lower() else answer
    parts = [p.strip(" .") for p in re.split(r";|\n|(?<=[.])\s+(?=[A-Z])", body) if p.strip(" .")]
    return [p[0].upper() + p[1:] for p in parts if len(p) > 3][:10]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]


def fallback_facts(
    gap: dict[str, Any], answer: str, target: dict[str, Any] | None, areas: list[str]
) -> list[Fact]:
    """Turn an answer into facts without an LLM, per gap rule."""
    rule, tid, area = gap["rule"], gap["target_id"], (areas[0] if areas else None)
    if rule in (handover_rules.MANDATORY, handover_rules.ASKED):
        # A standard or added question: the answer becomes knowledge the successor receives.
        return [
            Fact(
                kind="decision",
                key=f"dec:asked:{_slug(gap['id'])}",
                title=gap["title"],
                rationale=answer,
                area=area,
                quote=answer[:200],
            )
        ]
    if rule == "G1" and gap["target_kind"] == "Claim":
        return [
            Fact(
                kind="decision",
                key=f"dec:why:{_slug(tid)}",
                title=f"Why: {gap['title']}",
                rationale=answer,
                area=area,
                justified_by=None,
                quote=answer[:200],
            )
        ]
    if rule == "G1":
        return [
            Fact(
                kind="decision",
                key=tid,
                title=gap["title"],
                rationale=answer,
                area=area,
                quote=answer[:200],
            )
        ]
    if rule == "G8":
        return [
            Fact(
                kind="procedure",
                key=f"proc:how:{_slug(tid)}",
                title=f"How to {gap['title'][0].lower() + gap['title'][1:]}",
                steps=_steps(answer),
                handles=tid,
                area=area,
                quote=answer[:200],
            )
        ]
    if rule == "G6" and target:
        current = gap.get("context") or ""
        return [
            Fact(
                kind="decision",
                key=f"dec:current:{_slug(current or tid)}",
                title=f"Which is current: {target.get('title')}",
                rationale=answer,
                area=area,
                quote=answer[:200],
            )
        ]
    return []


EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["decision", "procedure"]},
                    "title": {"type": "string"},
                    "rationale": {"type": "string"},
                    "steps": {"type": "array", "items": {"type": "string"}},
                    "alternatives": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["kind", "title"],
            },
        },
        "current_value": {"type": "string"},
    },
    "required": ["facts"],
}


async def preview_answer(graph: Graph, llm: LLM, gap_id: str, answer: str) -> dict[str, Any]:
    """What would be recorded from this answer. Nothing is written until the leaver confirms."""
    gap = await graph.one("gap_get", {"id": gap_id})
    if not gap:
        raise NotFound(gap_id)
    target = await graph.one("knowledge_get", {"id": gap["target_id"]})
    areas = (
        (target or {}).get("areas")
        or (await graph.one("node_areas", {"id": gap["target_id"]}) or {}).get("areas")
        or []
    )
    facts = fallback_facts(gap, answer, target, areas)
    method = "rules"
    if gap["rule"] in ("G1", "G8", "G6") and facts:
        try:
            out = await llm.json(
                "You turn an employee's exit-interview answer into structured knowledge. Use only what the answer "
                "says. A decision needs a short title and the rationale in the employee's own terms. A procedure "
                "needs ordered, imperative steps.",
                f"Question: {gap['question']}\nAnswer: {answer}\nExpected kind: {facts[0].kind}",
                EXTRACT_SCHEMA,
            )
            first = (out.get("facts") or [None])[0]
            if first and first.get("kind") == facts[0].kind:
                f = facts[0]
                if gap["rule"] != "G6":  # keep the specific "Which is current: ..." title
                    f.title = first.get("title") or f.title
                if f.kind == "decision":
                    f.rationale = first.get("rationale") or f.rationale
                    f.alternatives = first.get("alternatives") or []
                else:
                    f.steps = first.get("steps") or f.steps
                method = llm.model
        except LLMUnavailable:
            pass
    choices = await claim_choices(graph, gap) if gap["rule"] == "G6" else []
    if choices and facts:
        # Neutral until the leaver picks; confirm_answer names the kept claim.
        values = " or ".join(str(c.get("value")) for c in choices if c.get("value"))
        facts[0].title = f"Which is current: {values}" if values else facts[0].title
    return {
        "gap": gap,
        "facts": [f.model_dump(exclude_none=True) for f in facts],
        "note": None if facts else "Saved as a note on the handover plan.",
        "method": method,
        "choices": choices,
        "suggested": handover_rules.suggest_claim(choices, answer) if choices else None,
    }


async def claim_choices(graph: Graph, gap: dict[str, Any]) -> list[dict[str, Any]]:
    """The two disagreeing claims behind a "sources disagree" question, for the leaver to pick."""
    out = []
    for cid in (gap["target_id"], gap.get("context")):
        k = await graph.one("knowledge_get", {"id": cid}) if cid else None
        if k:
            out.append({"id": k["id"], "title": k.get("title"), "value": k.get("value")})
    return out


async def confirm_answer(
    graph: Graph,
    gap_id: str,
    answer: str,
    facts: list[dict[str, Any]],
    keep: str | None = None,
) -> dict[str, Any]:
    """Record a confirmed answer. For "sources disagree", `keep` is the claim the leaver named as
    current (None: neither is, or they could not say; both stay as they are)."""
    gap = await graph.one("gap_get", {"id": gap_id})
    if not gap:
        raise NotFound(gap_id)
    if gap["status"] != "open":
        raise Conflict("This question is already answered or was dropped.")
    if gap["rule"] == "G6" and keep is None:
        # No pick sent (older clients, scripts): go by what the answer itself says, never by age.
        keep = handover_rules.suggest_claim(await claim_choices(graph, gap), answer)
    if gap["rule"] == "G6" and keep and keep not in (gap["target_id"], gap.get("context")):
        raise Conflict("Pick one of the two claims shown.")
    if gap["rule"] == "G6" and keep:
        kept = await graph.one("knowledge_get", {"id": keep})
        if kept:
            for item in facts:
                item["title"] = f"Current: {kept['title']}"
    emp, now = gap["employee_id"], now_ms()
    parsed = [Fact.model_validate(f) for f in facts]
    target = await graph.one("knowledge_get", {"id": gap["target_id"]})
    areas = (
        (target or {}).get("areas")
        or (await graph.one("node_areas", {"id": gap["target_id"]}) or {}).get("areas")
        or []
    )
    src = SourceIn(
        id=_id("src:answer"),
        kind="InterviewAnswer",
        system="handovers",
        title=f"Exit interview: {gap['title']}",
        text=f"Q: {gap['question']}\nA: {answer}",
        occurred_at=datetime.fromtimestamp(now / 1000, tz=UTC).isoformat(),
        author=emp,
        areas=areas,
        facts=parsed,
    )
    await write_source(graph, src, origin="interview")
    # Link the new knowledge to what the gap was about.
    for f in parsed:
        if gap["rule"] == "G1" and gap["target_kind"] == "Claim" and f.kind == "decision":
            await graph.run("knowledge_justify", {"id": gap["target_id"], "decision": f.key})
        if gap["rule"] == "G6" and f.kind == "decision" and keep:
            # The leaver named the current claim. Both claims stay; the other is closed, and their
            # answer is a decision of its own that CONFIRMS one and RESOLVES the other.
            other = gap["target_id"] if keep == gap.get("context") else gap.get("context")
            if other:
                await graph.run(
                    "claim_resolve", {"decision": f.key, "keep": keep, "old": other, "now": now}
                )
    if gap["rule"] in ("G2", "G4") and target:
        await graph.run(
            "knowledge_add_evidence",
            {"id": gap["target_id"], "source": src.id, "quote": answer[:200], "documented": True},
        )
    await graph.run("gap_resolve", {"id": gap_id, "answer": src.id, "now": now})
    await recompute_confidence(graph)
    await audit(
        graph,
        gap["handover_id"],
        "interview.answered",
        {"gap": gap_id, "facts": [f.key for f in parsed]},
        emp,
    )
    return {"source": src.id, "facts": [f.key for f in parsed]}


async def dismiss_gap(graph: Graph, gap_id: str, by: str = "", reason: str = "") -> None:
    gap = await graph.one("gap_get", {"id": gap_id})
    if not gap:
        raise NotFound(gap_id)
    if gap["rule"] == handover_rules.MANDATORY:
        raise Conflict("Company policy asks every leaver this question; it can't be dropped.")
    await graph.run(
        "gap_dismiss", {"id": gap_id, "by": by, "now": now_ms(), "reason": reason or "dropped"}
    )
    await audit(
        graph, gap["handover_id"], "interview.dismissed", {"gap": gap_id, "reason": reason}, by
    )


# ---- transfer ------------------------------------------------------------------------------------


async def transfer_preview(graph: Graph, hid: str) -> dict[str, Any]:
    h = await get(graph, hid)
    if not h.get("successor_id"):
        return {"ready": False, "reason": "Choose a successor first.", "include": [], "exclude": []}
    rows = await graph.read(
        "transfer_candidates",
        {"emp": h["employee_id"], "successor": h["successor_id"], "now": now_ms()},
    )
    include: list[dict[str, Any]] = []
    exclude: list[dict[str, Any]] = []
    for r in rows:
        ok, reason = policy.transfer_decision(r)
        (include if ok else exclude).append(
            {"id": r["id"], "kind": r["kind"], "title": r["title"], "reason": reason}
        )
    transferred = h["status"] == "transferred"
    if transferred:
        # Follow-up: only what was captured since the last approval is new; the rest already moved.
        exclude = [x for x in exclude if x["reason"] != "already known"]
    p = await analysis.person(graph, h["employee_id"]) or {}
    return {
        "ready": True,
        "transferred": transferred,
        "successor": h["successor"],
        "include": include,
        "exclude": exclude,
        "responsibilities": [r["title"] for r in p.get("responsibilities", [])],
        "relationships": [f"{s['name']} ({s.get('org')})" for s in p.get("stakeholders", [])],
        "open_questions": sum(1 for g in h["gaps"] if g["interview"] and g["status"] == "open"),
    }


async def pending_followup(graph: Graph, h: dict[str, Any]) -> int:
    """Knowledge captured since the transfer was approved, not yet with the successor."""
    if h.get("status") != "transferred" or not h.get("successor_id"):
        return 0
    return len((await transfer_preview(graph, h["id"]))["include"])


async def approve_and_transfer(
    graph: Graph, hid: str, approved_by: str, comment: str = ""
) -> dict[str, Any]:
    preview = await transfer_preview(graph, hid)
    if not preview["ready"]:
        raise Conflict(preview["reason"])
    h = await get(graph, hid)
    if h["status"] == "cancelled":
        raise Conflict("This handover was cancelled.")
    followup = h["status"] == "transferred"
    if not followup:
        # The successor may have resigned or left since they were chosen.
        await check_successor(graph, h["employee_id"], h["successor_id"], confirmed=True)
    if followup and not preview["include"]:
        raise Conflict("Nothing new to hand over since the last approval.")
    now = now_ms()
    tid = _id("tr")
    await graph.run("transfer_create", {"handover": hid, "id": tid, "now": now})
    await graph.run(
        "transfer_include_knowledge",
        {"id": tid, "items": [{"id": i["id"], "reason": i["reason"]} for i in preview["include"]]},
    )
    await graph.run(
        "transfer_exclude_knowledge",
        {"id": tid, "items": [{"id": i["id"], "reason": i["reason"]} for i in preview["exclude"]]},
    )
    if not followup:
        await graph.run("transfer_include_responsibilities", {"id": tid, "now": now})
        await graph.run("transfer_include_stakeholders", {"id": tid, "now": now})
    await graph.run(
        "approval_create",
        {
            "transfer": tid,
            "by": approved_by,
            "id": _id("ap"),
            "decision": "approved",
            "now": now,
            "comment": comment,
        },
    )
    k = await graph.run("transfer_apply_knowledge", {"id": tid, "now": now})
    await graph.run("transfer_mark", {"id": tid, "status": "applied", "now": now})
    if followup:
        # Knowledge the leaver captured after the first approval (e.g. late exit-interview answers).
        counts = {
            "knowledge": k[0]["applied"] if k else 0,
            "responsibilities": 0,
            "relationships": 0,
            "excluded": len(preview["exclude"]),
        }
        await audit(graph, hid, "transfer.followup", {"transfer": tid, **counts}, approved_by)
        return {"transfer": tid, "followup": True, **counts}
    r = await graph.run(
        "transfer_apply_responsibilities", {"id": tid, "now": now, "open": 253402300799000}
    )
    s = await graph.run(
        "transfer_apply_stakeholders", {"id": tid, "now": now, "open": 253402300799000}
    )
    await graph.run("handover_set_status", {"id": hid, "status": "transferred", "now": now})
    # The leaver is NOT marked as left here: they work, sign in and can answer late questions
    # until their last day, when the `depart` job ends it. A joining successor becomes active.
    if (await graph.one("successor_candidate", {"id": h["successor_id"]}) or {}).get(
        "status"
    ) == "incoming":
        await graph.run("employee_set_status", {"id": h["successor_id"], "status": "active"})
    counts = {
        "knowledge": k[0]["applied"] if k else 0,
        "responsibilities": r[0]["applied"] if r else 0,
        "relationships": s[0]["applied"] if s else 0,
        "excluded": len(preview["exclude"]),
    }
    await audit(graph, hid, "transfer.applied", {"transfer": tid, **counts}, approved_by)
    return {"transfer": tid, **counts}


async def reject_transfer(graph: Graph, hid: str, by: str, comment: str) -> dict[str, Any]:
    """The approver sends the transfer back with a reason. Nothing moves; it can be approved later."""
    h = await get(graph, hid)
    if h["status"] in ("cancelled", "transferred"):
        raise Conflict("Only a transfer waiting for approval can be rejected.")
    if len(comment.strip()) < 5:
        raise Conflict("Say what needs to change, so the leaver and HR know what to fix.")
    tid = _id("tr")
    await graph.run(
        "transfer_reject",
        {
            "handover": hid,
            "id": tid,
            "approval": _id("ap"),
            "by": by,
            "now": now_ms(),
            "comment": comment.strip(),
        },
    )
    await audit(graph, hid, "transfer.rejected", {"transfer": tid, "comment": comment.strip()}, by)
    return {"transfer": tid, "decision": "rejected", "comment": comment.strip()}


async def cancel(graph: Graph, hid: str, by: str, reason: str) -> dict[str, Any]:
    """A withdrawn resignation, within the policy's window: the handover stops, pending account
    proposals are withdrawn and scheduled jobs are cancelled. The person stays an employee."""
    h = await get(graph, hid)
    p = await org_policy.load(graph)
    window = handover_rules.cancel_window(h, p, now_ms())
    if not window["allowed"]:
        raise Conflict(window["reason"])
    if len(reason.strip()) < 5:
        raise Conflict("Give a reason, for example: resignation withdrawn on 14 Oct.")
    now = now_ms()
    await graph.run("handover_cancel", {"id": hid, "now": now, "by": by, "reason": reason.strip()})
    await graph.run("reassignments_close", {"handover": hid, "now": now})
    await graph.run("jobs_cancel_for_handover", {"handover": hid, "now": now})
    await audit(
        graph, hid, "handover.cancelled", {"reason": reason.strip(), "policy": p["version"]}, by
    )
    return {"id": hid, "status": "cancelled"}


async def depart(graph: Graph, hid: str) -> dict[str, Any]:
    """The last day (run by the `depart` job): the leaver is marked as left and every access they
    still hold ends now. History is kept. A cancelled handover does nothing."""
    h = await graph.one("handover_get", {"id": hid})
    if not h or h["status"] == "cancelled":
        return {"skipped": True}
    now = now_ms()
    if (h.get("effective_at") or 0) > now:
        return {"skipped": True, "reason": "not the last day yet"}
    rows = await graph.run("leaver_access_end", {"emp": h["employee_id"], "now": now})
    await graph.run("employee_depart", {"id": h["employee_id"], "now": now})
    ended = rows[0]["ended"] if rows else 0
    await audit(
        graph,
        hid,
        "employee.departed",
        {"employee": h["employee_id"], "access_ended": ended},
        "system",
    )
    return {"departed": h["employee_id"], "access_ended": ended}


async def capture_plan(graph: Graph, h: dict[str, Any], can_read: bool) -> dict[str, Any]:
    """The days left as a plan (handover_rules.capture_plan), from the handover and the graph."""
    from services import access

    core, extra = handover_rules.interview_sets(h["gaps"])
    if not can_read:
        core, extra = access.redact_gaps(core), access.redact_gaps(extra)
    p = await org_policy.load(graph)
    person = await analysis.person(graph, h["employee_id"]) or {}
    effective = h.get("effective_at") or now_ms()
    solo = [r for r in person.get("responsibilities") or [] if not r.get("co_owners")]
    recurring = [r for r in solo if r.get("next_due") and r["next_due"] <= effective]
    contacts = [s for s in person.get("stakeholders") or [] if not s.get("other_contacts")]
    accounts = [
        {"name": g["title"]}
        for g in h["gaps"]
        if g["rule"] == "G7A" and g.get("resolution") != "reassigned"
    ]
    return handover_rules.capture_plan(
        now_ms(),
        effective,
        org_policy.zone(p),
        [g for g in core if g["status"] == "open"],
        [g for g in extra if g["status"] == "open"],
        recurring,
        contacts,
        accounts,
        h.get("successor"),
        solo,
        grouped=not can_read,
    )
