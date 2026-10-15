"""Liveness, readiness and UI status endpoints."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel

from core.config import APP_VERSION
from core.falkordb import FalkorDBClient

router = APIRouter(tags=["health"])


def get_falkordb(request: Request) -> FalkorDBClient:
    client: FalkorDBClient = request.app.state.falkordb
    return client


FalkorDep = Annotated[FalkorDBClient, Depends(get_falkordb)]


class FalkorDBHealth(BaseModel):
    ok: bool
    graph: str
    module_version: int | None
    error: str | None


class SystemStatus(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    falkordb: FalkorDBHealth


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness: the process is up. Does not touch FalkorDB."""
    return {"status": "ok"}


@router.get("/readyz", response_model=SystemStatus)
async def readyz(falkordb: FalkorDep, response: Response) -> SystemStatus:
    """Readiness: 200 only when FalkorDB answers."""
    result = await _system_status(falkordb)
    if result.status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result


@router.get("/api/status", response_model=SystemStatus)
async def api_status(falkordb: FalkorDep) -> SystemStatus:
    """Status for the UI. Always 200; the body says what is degraded."""
    return await _system_status(falkordb)


async def _system_status(falkordb: FalkorDBClient) -> SystemStatus:
    db = await falkordb.status()
    return SystemStatus(
        status="ok" if db.ok else "degraded",
        version=APP_VERSION,
        falkordb=FalkorDBHealth(
            ok=db.ok, graph=falkordb.graph_name, module_version=db.module_version, error=db.error
        ),
    )
