"""FastAPI application entry point.

Dev:  uv run fastapi dev main.py
Prod: uv run fastapi run main.py
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import (
    alerts,
    auth,
    candidates,
    companion,
    connectors,
    handovers,
    health,
    me,
    meta,
    org,
    people,
    ramp,
    readiness,
    uploads,
    xray,
)
from core.config import APP_VERSION, Settings, get_settings
from core.falkordb import FalkorDBClient
from core.graph import Graph, QueryCatalog
from core.llm import LLM
from core.logging import configure_logging, get_logger
from core.trace import HEADER as TRACE_HEADER
from core.trace import TraceMiddleware
from services import jobs, tech_graph


async def load_project_graph(graph: Graph, settings: Settings, log: Any) -> None:
    """The architecture view's graph; a problem here only warns, the product runs without it."""
    try:
        if await tech_graph.ensure(graph, tech_graph.architecture_path(settings.graph_dir)):
            log.info("project_graph_loaded", graph=tech_graph.PROJECT_GRAPH)
    except Exception as exc:  # never block startup on the explainer
        log.warning("project_graph_not_loaded", error=str(exc))


async def ensure_platform_admin(graph: Graph, settings: Settings, log: Any) -> None:
    """Create the platform admin's sign-in at startup; a Keycloak that is not up yet only warns."""
    from core.keycloak import KeycloakError
    from services.identity import ensure_platform_admin as ensure

    try:
        await ensure(graph, settings)
    except (KeycloakError, httpx.HTTPError) as exc:
        log.warning("platform_admin_not_ready", error=str(exc))


async def print_demo_sign_in(graph: Graph, settings: Settings) -> None:
    """Local development only: who to sign in as, printed once at startup in plain ASCII.

    Shown only when sign-in is on and DEMO_USER_PASSWORD is set (never anywhere real, where that
    setting stays empty and people sign in with Google or Microsoft).
    """
    password = settings.demo_user_password.get_secret_value()
    if not settings.sso_enabled or not password:
        return
    from services.access import personas

    emails = {p["id"]: p.get("email") for p in await graph.read("people_directory", {})}
    rows = [
        (p["label"], p["name"], emails[p["id"]])
        for p in await personas(graph)
        if emails.get(p["id"])
    ]
    width = max((len(f"{label}: {name}") for label, name, _ in rows), default=10)
    lines = [
        "",
        "Demo sign-in (local development, from DEMO_USER_PASSWORD in .env)",
        f"  Open {settings.app_public_url.rstrip('/')}/login -> Continue with email",
        "  Username or email + password:",
    ]
    lines += [
        f"    {f'{label}: {name}':<{width}}  {email}  /  {password}" for label, name, email in rows
    ]
    lines.append("  Any other employee's email works with the same password.")
    admin = settings.platform_admin_password.get_secret_value()
    if admin:
        lines.append(
            f"  Platform admin (integrations, sign-in): {settings.platform_admin_email}  /  {admin}"
        )

    # These accounts exist in Keycloak only once people are synced to it. Do that now, so signing
    # in works right after startup; say how to do it by hand when Keycloak isn't reachable yet.
    from core.keycloak import KeycloakError
    from services.identity import provision_people

    try:
        synced = (await provision_people(graph, settings))["people"]
        lines.append(f"  {synced} people synced to Keycloak, so these accounts are ready.")
    except (KeycloakError, httpx.HTTPError):
        lines.append(
            "  Could not sync people to Keycloak (is it running? "
            "docker compose --profile auth up -d keycloak)."
        )
    lines += [
        "",
        '  Note: if email + password sign-in does not work ("Invalid username or password"):',
        "    1. Open the login page -> Explore the demo as a guest",
        "    2. View as (bottom left) -> Meera Iyer (HR & Admin)",
        "    3. Integrations -> Sign-in -> Sync people",
        "    4. Sign in again with the email and password above",
    ]
    print("\n".join([*lines, ""]), flush=True)


def create_app(settings: Settings | None = None, falkordb: FalkorDBClient | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    log = get_logger("handovers")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client = falkordb or FalkorDBClient(settings)
        app.state.falkordb = client
        catalog = QueryCatalog(settings.graph_dir)
        app.state.graph = Graph(client, catalog)
        app.state.project_graph = Graph(client, catalog, graph_name=tech_graph.PROJECT_GRAPH)
        app.state.llm = LLM(settings)
        db = await client.status()
        if db.ok and settings.seed_on_start and not await client.graph_exists():
            from seed.load import bootstrap, load, open_scenario

            await bootstrap(app.state.graph)
            stats = await load(app.state.graph)
            await open_scenario(app.state.graph)
            log.info("seeded", sources=stats.sources, facts=stats.facts)
        if db.ok:
            await load_project_graph(app.state.project_graph, settings, log)
        log.info(
            "startup",
            graph=client.graph_name,
            falkordb_ok=db.ok,
            falkordb_error=db.error,
            llm=app.state.llm.model,
            queries=len(app.state.graph.catalog.names()),
        )
        if db.ok and not await client.graph_exists():
            log.warning(
                "graph_empty",
                hint="Load the sample company: uv run python -m seed.load --reset "
                "(or set SEED_ON_START=true in .env and restart)",
            )
        elif db.ok:
            await ensure_platform_admin(app.state.graph, settings, log)
            await print_demo_sign_in(app.state.graph, settings)
        worker = None
        if db.ok and settings.jobs_enabled:
            # Background jobs (digest, last-day alerts, departures, letters): services/jobs.py.
            worker = asyncio.create_task(jobs.worker(app.state.graph, settings.jobs_poll_seconds))
        try:
            yield
        finally:
            if worker:
                worker.cancel()
            await app.state.llm.close()
            await client.close()
            log.info("shutdown")

    app = FastAPI(title="Handovers API", version=APP_VERSION, lifespan=lifespan)
    app.add_middleware(TraceMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[TRACE_HEADER],
    )
    for module in (
        health,
        people,
        handovers,
        companion,
        uploads,
        meta,
        me,
        xray,
        ramp,
        readiness,
        connectors,
        auth,
        alerts,
        candidates,
        org,
    ):
        app.include_router(module.router)
    return app


app = create_app()
