"""Uploads and the review queue."""

import json
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from api.deps import GraphDep, LLMDep
from ingestion import pipeline

router = APIRouter(prefix="/api", tags=["uploads"])
MAX_BYTES = 15 * 1024 * 1024


@router.post("/uploads", status_code=201)
async def upload(
    graph: GraphDep,
    llm: LLMDep,
    file: Annotated[UploadFile, File()],
    employee_id: Annotated[str, Form()] = "",
) -> dict[str, Any]:
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
async def uploads(graph: GraphDep) -> list[dict[str, Any]]:
    return await graph.read("uploads_list", {})


@router.get("/review")
async def review(graph: GraphDep) -> list[dict[str, Any]]:
    rows = await graph.read("review_list", {})
    for r in rows:
        fact = json.loads(r.pop("fact") or "{}")
        r["quote"] = fact.get("quote")
    return rows


class DecisionIn(BaseModel):
    approve: bool
    employee_id: str | None = None


@router.post("/review/{rid}")
async def decide(rid: str, body: DecisionIn, graph: GraphDep) -> dict[str, Any]:
    try:
        return await pipeline.decide_review(graph, rid, body.approve, body.employee_id)
    except KeyError as exc:
        raise HTTPException(404, "Not found or already decided") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
