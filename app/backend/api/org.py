"""The organisation's exit policy, and the background job queue (HR and the platform admin)."""

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.deps import CallerDep, GraphDep, forbid
from core.clock import now_ms
from services import access, jobs, org_policy

router = APIRouter(prefix="/api", tags=["organisation"])

POLICY_EDITORS = "Only HR or the platform admin can change the exit policy."


def _can_edit(caller: access.Caller | None) -> bool:
    return caller is None or "hr" in caller.roles or access.can_configure(caller)


def _can_see(caller: access.Caller | None) -> bool:
    return caller is None or bool(caller.roles & {"hr", "exec", "platform_admin"})


@router.get("/policy")
async def get_policy(graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    forbid(_can_see(caller), POLICY_EDITORS)
    p = await org_policy.load(graph)
    return p | {"can_edit": _can_edit(caller), "defaults": org_policy.DEFAULTS}


class PolicyIn(BaseModel):
    withdrawal_days: int
    letter_on_last_day: bool
    mandatory_questions: list[str]
    hr_teams: list[str]
    hr_is_it: bool = True
    exec_titles: list[str]
    role_groups: dict[str, str] = {}
    timezone: str
    country_code: str
    digest_hour: int


@router.put("/policy")
async def put_policy(body: PolicyIn, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    forbid(_can_edit(caller), POLICY_EDITORS)
    data = body.model_dump()
    data["mandatory_questions"] = [q.strip() for q in data["mandatory_questions"] if q.strip()]
    data["hr_teams"] = [t.strip() for t in data["hr_teams"] if t.strip()]
    data["exec_titles"] = [t.strip() for t in data["exec_titles"] if t.strip()]
    problems = org_policy.validate(data)
    if problems:
        raise HTTPException(422, " ".join(problems))
    saved = await org_policy.save(graph, data, caller.id if caller else "")
    return await get_policy(graph, caller) | {"version": saved["version"]}


@router.get("/jobs")
async def list_jobs(graph: GraphDep, caller: CallerDep) -> list[dict[str, Any]]:
    """The queue: what waits and what ran, newest first."""
    forbid(_can_edit(caller), "Only HR or the platform admin can see background jobs.")
    rows = await graph.read("job_list", {"limit": 60})
    return [
        r
        | {
            "label": jobs.describe(r),
            "result": json.loads(r["result"]) if r.get("result") else None,
        }
        for r in rows
    ]


@router.post("/jobs/{jid}/run")
async def run_job(jid: str, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    """Run a queued (or failed) job now instead of at its time."""
    forbid(_can_edit(caller), "Only HR or the platform admin can run jobs.")
    if not await graph.run("job_run_now", {"id": jid, "now": now_ms()}):
        raise HTTPException(404, "No queued or failed job with that id")
    ran = await jobs.run_due(graph)
    return {"ran": [{"id": r["id"], "kind": r["kind"], "status": r["status"]} for r in ran]}
