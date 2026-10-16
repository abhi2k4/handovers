"""Graph X-ray trace: every /api request gets a trace id; queries are recorded only inside one."""

import asyncio

from core import trace


def test_record_is_a_noop_outside_a_request() -> None:
    trace.record("person_get", None, {"emp": "x"}, 1, 2.0, "read")  # must not raise


def test_middleware_records_queries_for_api_requests() -> None:
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient

    async def endpoint(request: object) -> JSONResponse:
        await asyncio.sleep(0)
        trace.record("person_get", None, {"emp": "emp:nisha"}, 1, 3.21, "read")
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/api/thing", endpoint), Route("/healthz", endpoint)])
    app.add_middleware(trace.TraceMiddleware)
    client = TestClient(app)

    response = client.get("/api/thing")
    trace_id = response.headers[trace.HEADER]
    recorded = trace.get(trace_id)
    assert recorded is not None and recorded["path"] == "/api/thing"
    assert recorded["queries"] == [
        {
            "name": "person_get",
            "label": None,
            "params": {"emp": "emp:nisha"},
            "rows": 1,
            "ms": 3.2,
            "mode": "read",
        }
    ]
    assert trace.HEADER not in client.get("/healthz").headers
