# app/backend/

FastAPI + LangGraph backend. FalkorDB is its only stateful store.

**Status:** skeleton running: settings, structured logging, FalkorDB connection,
`/healthz`, `/readyz`, `/api/status`, unit and integration tests.

## Run on the host (dev, live reload)

Prerequisites: [uv](https://docs.astral.sh/uv/), and FalkorDB running from the repo root
(`docker compose up -d falkordb`). If the full stack is up, stop the backend container first:
`docker compose stop backend`.

**bash**
```bash
cd app/backend
uv sync
uv run uvicorn main:app --reload
```
**PowerShell**
```powershell
cd app\backend
uv sync
uv run uvicorn main:app --reload
```

**Or with pip** (Python 3.12):

| bash | PowerShell |
|---|---|
| `python -m venv .venv` | `python -m venv .venv` |
| `source .venv/bin/activate` (Git Bash: `source .venv/Scripts/activate`) | `.venv\Scripts\Activate.ps1` |
| `pip install -r requirements-dev.txt` | `pip install -r requirements-dev.txt` |
| `uvicorn main:app --reload` | `uvicorn main:app --reload` |

(`uvicorn` rather than `fastapi dev`: the FastAPI CLI prints emoji banners; the console stays plain
ASCII. With sign-in on and `DEMO_USER_PASSWORD` set, startup prints who to sign in as.)

- API: http://localhost:8000 · interactive docs: http://localhost:8000/docs
- Settings come from the repo-root `.env` (`FALKORDB_HOST=localhost` on the host). The Docker
  container overrides the host to `falkordb`.
- uv installs Python 3.12 automatically if it is missing (`.python-version`).

## Dependencies (uv and pip kept in sync)

| File | Purpose |
|---|---|
| `pyproject.toml` | Direct dependencies (edit with `uv add` / `uv remove`) |
| `uv.lock` | Exact versions of everything (source of truth) |
| `requirements.txt` | pip export of runtime deps (generated, do not edit) |
| `requirements-dev.txt` | pip export of runtime + dev deps (generated, do not edit) |

To add a package, run `uv add <package>` (or `uv add --dev <package>`), then regenerate the pip
files from the repo root with `scripts/sync-requirements.sh` (bash) or
`.\scripts\sync-requirements.ps1` (PowerShell). Commit all four files together. CI fails if the pip
files drift from `uv.lock`.

## Checks

Same commands in bash and PowerShell (run inside `app/backend`):
```
uv run pytest                  # all tests (integration tests skip if FalkorDB is down)
uv run pytest -m integration   # only tests that hit FalkorDB
uv run ruff check .            # lint
uv run ruff format .           # format
uv run mypy                    # type-check (strict)
```

## Endpoints

Interactive list with request and response shapes: http://localhost:8000/docs. Groups:
health (`/healthz`, `/readyz`, `/api/status`), meta, people, handovers, companion, uploads,
review, and me (`/api/me`, `/api/personas`, `/api/kpis`).

**Access:** every rule is in `services/access.py` (HR runs handovers but cannot read answers or
approve; only the leaver's manager approves; people ask and change privacy only as themselves). The
demo caller comes from the `X-View-As: <employee id>` header; without it the API is unrestricted.
This is a demo stand-in, not authentication (Keycloak later: `docs/identity-and-access.md`).

**LLM (optional):** set `LLM_PROVIDER=groq`, `LLM_MODEL=openai/gpt-oss-120b` and `GROQ_API_KEY` in
the repo-root `.env` (key from https://console.groq.com/keys). Without a key everything still works with
deterministic templates. The copilot (`POST /api/copilot`, the "Ask anything" bar) answers only from
the app guide in `services/copilot.py` and the caller's own memory.

**Graph X-ray:** `core/trace.py` records every named query an `/api` request runs (name, params,
rows, ms) and returns the trace id in the `X-Trace-Id` header. `GET /api/xray/{id}` returns those
queries with their Cypher; `GET /api/xray/subgraph?id=<node>` returns the node and up to 40
neighbours under the same access rules (private and personal items only in your own graph).

**Successor ramp-up plan:** `services/ramp.py` builds a first-month plan from the leaver's work
in the graph (access, recurring work by cadence, people only they know, decisions to read) and
stores it as `RampPlan`/`RampItem` nodes. `GET|POST /api/handovers/{id}/ramp`,
`POST /api/handovers/{id}/ramp/approve` (manager only), `POST /api/ramp-items/{id}` (manager edits
a draft; the successor ticks items of an approved plan).

**Readiness and key-person risk:** `services/readiness.py` (pure) turns a handover into six
last-day checks with an owner and a link each: `GET /api/handovers/{id}/readiness`.
`POST /api/handovers/{id}/accounts/{account}/reassign` gives a sole-admin account to the successor
(IT, HR or the manager) and closes its G7A gap. `POST /api/responsibilities/{id}/backup` adds a
backup owner (HR for anyone; a manager picks from their own team). Incoming employees count as
admins once they have access.

**Follow-up transfers:** after the first approval, `GET /api/handovers/{id}/transfer` lists only
knowledge captured since (`transferred: true`), and `POST` approves it as a follow-up that moves
knowledge only. `analysis.person(graph, emp, at=...)` reads what someone held at an earlier time;
the ramp-up plan uses it when created after the approval.

**Data connectors:** `connectors/` has one package per platform (Entra ID, Slack, GitHub, Jira, Notion, HubSpot, Salesforce); `services/sync.py`
runs one through the upload review gate and keeps its cursor in a `Connector` node.
`GET /api/connectors` (state plus the connect form, secrets masked), `PUT|DELETE /api/connectors/{id}/config`
(stored encrypted, `core/security.py`, `services/connector_config.py`), `POST /api/connectors/{id}/sync`
(HR and IT). Setup per platform:
[docs/connectors.md](../../docs/connectors.md).

**Sign-in:** Keycloak with Backend-for-Frontend sessions (`core/keycloak.py`, `api/auth.py`,
`services/identity.py`): `/api/auth/{config,login,callback,session,logout}`, plus sign-in provider setup
(`identity/`: one package per provider, Microsoft Entra ID and Google Workspace) and "Sync people" for HR and IT. A signed-in session decides the caller (`api/deps.py`);
otherwise the View-as header for guests. Off while `KEYCLOAK_URL` is empty.
[docs/identity-and-access.md](../../docs/identity-and-access.md) §0.

**Ask (companion):** `POST /api/companion/{emp}/ask` answers only from that person's memory
(`services/companion.py`): targeted retrieval first; overview questions and misses go to the LLM with
a digest of the person's items (personal notes never included) and must cite item ids; short
follow-ups use the conversation's previous turn. `GET /api/companion/{emp}/profile` returns what the
memory holds and suggested questions built from it.

**Exit rules, policy and jobs:** successor checks, the approver fallback, cancellation within the
withdrawal window, mandatory and added interview questions, account handovers (proposed, then
approved by HR), two-step clearance and the relieving letter are described in
[docs/handover-rules.md](../../docs/handover-rules.md). `GET|PUT /api/policy` is the company's
exit policy (`services/org_policy.py`). Background jobs (daily digest, last-day warnings, alerts
held over quiet hours, departures, scheduled letters) run in a worker inside this process
(`services/jobs.py`, `JOBS_ENABLED`, `JOBS_POLL_SECONDS`); the queue lives in FalkorDB as `Job`
nodes. `GET /api/jobs` lists it and `POST /api/jobs/{id}/run` runs one now (the demo clock is
pinned, so scheduled jobs never come due on their own).

**Demo data:** reset to the clean sample company with `uv run python -m seed.load --reset`
(without `--reset` it adds to the existing graph).

## Layout

```
app/backend/
  main.py          FastAPI app + lifespan (FalkorDB client, query catalogue, optional seeding)
  core/            config, logging, clock, falkordb (client), graph (named-query runner), llm,
                   keycloak, security, trace                                     (core/README.md)
  api/             HTTP routers, one per area                                    (api/README.md)
  services/        the product's logic: access rules, workflow, read models, generators,
                   companion, sync, identity, the project graph            (services/README.md)
  ingestion/       upload pipeline: schema, extraction, review queue, single graph writer
  connectors/      one package per data platform (<name>/connector.py): API -> sources and people
  identity/        one package per sign-in provider (<name>/provider.py): what Keycloak is given
  seed/            sample company: generate, load (python -m seed.load), samples
  bench/           benchmark runner (python -m bench.run)
  tests/
    unit/          no I/O
    integration/   real FalkorDB on throwaway graphs (skipped when FalkorDB is not reachable)
  pyproject.toml   dependencies + tool config (uv, ruff, mypy, pytest)
  uv.lock          locked versions (uv)
  requirements*.txt  pip exports of uv.lock (generated)
  Dockerfile       image used by the root docker-compose.yml (built from the repo root)
```
