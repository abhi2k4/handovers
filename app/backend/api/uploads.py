"""Uploads and the review queue."""

import json
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from api.deps import CallerDep, GraphDep, LLMDep, forbid
from ingestion import pipeline
from services import access

router = APIRouter(prefix="/api", tags=["uploads"])
MAX_BYTES = 15 * 1024 * 1024
HR_ONLY = "Only HR adds sources and reviews what enters the memory."


@router.post("/uploads", status_code=201)
async def upload(
    graph: GraphDep,
    llm: LLMDep,
    file: Annotated[UploadFile, File()],
    caller: CallerDep,
    employee_id: Annotated[str, Form()] = "",
) -> dict[str, Any]:
    forbid(access.can_curate_sources(caller), HR_ONLY)
    if file.size is not None and file.size > MAX_BYTES:
        raise HTTPException(413, "Files up to 15 MB.")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Files up to 15 MB.")
    try:
        return await pipeline.ingest(
            graph, llm, file.filename or "upload", data, employee_id or None
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/uploads")
async def uploads(graph: GraphDep, caller: CallerDep) -> list[dict[str, Any]]:
    forbid(access.can_curate_sources(caller), HR_ONLY)
    return await graph.read("uploads_list", {})


@router.get("/review")
async def review(graph: GraphDep, caller: CallerDep) -> list[dict[str, Any]]:
    forbid(access.can_curate_sources(caller), HR_ONLY)
    rows = await graph.read("review_list", {})
    for r in rows:
        fact = json.loads(r.pop("fact") or "{}")
        r["quote"] = fact.get("quote")
    return rows


class DecisionIn(BaseModel):
    approve: bool
    employee_id: str | None = None


@router.post("/review/{rid}")
async def decide(rid: str, body: DecisionIn, graph: GraphDep, caller: CallerDep) -> dict[str, Any]:
    forbid(access.can_curate_sources(caller), HR_ONLY)
    try:
        return await pipeline.decide_review(graph, rid, body.approve, body.employee_id)
    except KeyError as exc:
        raise HTTPException(404, "Not found or already decided") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
