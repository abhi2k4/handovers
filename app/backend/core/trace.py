"""Graph X-ray: record which named queries each API request ran.

The middleware starts a trace per `/api` request and returns its id in the `X-Trace-Id` header.
`core.graph.Graph` appends every query it runs to the current trace. `GET /api/xray/{id}` reads it
back. Traces live in memory (the most recent `MAX_TRACES`) and hold query names, parameters, row
counts and timings, never results.
"""

import time
import uuid
from collections import OrderedDict
from contextvars import ContextVar
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

MAX_TRACES = 300
HEADER = "X-Trace-Id"

_current: ContextVar[list[dict[str, Any]] | None] = ContextVar("graph_trace", default=None)
_traces: OrderedDict[str, dict[str, Any]] = OrderedDict()


def record(
    name: str, label: str | None, params: dict[str, Any], rows: int, ms: float, mode: str
) -> None:
    """Called by the query runner; a no-op outside a traced request."""
    queries = _current.get()
    if queries is not None:
        queries.append(
            {
                "name": name,
                "label": label,
                "params": params,
                "rows": rows,
                "ms": round(ms, 1),
                "mode": mode,
            }
        )


def get(trace_id: str) -> dict[str, Any] | None:
    return _traces.get(trace_id)


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if not path.startswith("/api/") or path.startswith("/api/xray"):
            return await call_next(request)
        queries: list[dict[str, Any]] = []
        token = _current.set(queries)  # the endpoint task inherits this list and appends to it
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            _current.reset(token)
        trace_id = uuid.uuid4().hex
        _traces[trace_id] = {
            "id": trace_id,
            "method": request.method,
            "path": path,
            "ms": round((time.perf_counter() - started) * 1000, 1),
            "queries": queries,
        }
        while len(_traces) > MAX_TRACES:
            _traces.popitem(last=False)
        response.headers[HEADER] = trace_id
        return response
