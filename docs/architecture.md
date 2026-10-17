# Architecture: System, Stack, Repository, API, Frontend, Ingestion, Testing, Deployment

## H. System architecture

```
                ┌──────────────────────────── app/frontend (React + Vite + TS + Tailwind) ─────────────┐
                │ Dashboard · Handover · Gaps/Interview · Review/Approval · Successor chat · Lineage   │
                └───────────────────────────────┬──────────────────────────────────────────────────────┘
                                                │ REST/JSON + SSE (chat streaming)
┌───────────────────────────────────────────────┴──────────────────────────────────────────────────┐
│ app/backend (FastAPI, modular monolith)                                                          │
│  api/ (routers) ─► services/ (OpenHandover, RunAnalysis, AnswerGap, Approve, Transfer, Ask)       │
│           │                      │                                                               │
│           ▼                      ▼                                                               │
│  agents/ (LangGraph)       services/ also holds pure rules: policies, gap rules, scoring         │
│   HandoverOrchestrator           ▲                                                               │
│   InterviewAgent                 │ ports (typed interfaces)                                      │
│   PersonalMemoryAgent            │                                                               │
│           │                core/                                                                 │
│           └──────────────► graph repo (falkordb-py async) · LLM adapter · checkpointer · logging │
└───────────────────────────────────────────────┬──────────────────────────────────────────────────┘
                                                │ Redis protocol
                           ┌────────────────────┴───────────────────┐
                           │ FalkorDB (graph per tenant)            │
                           │ Sources · Knowledge · Memory · Workflow│
                           │ + LangGraph checkpoints (FalkorDBSaver)│
                           └────────────────────────────────────────┘
```

FalkorDB is the **only** stateful store. It holds the knowledge, memory, sessions, workflow state,
audit and agent checkpoints.

## Stack (16)

| Concern | Choice | Note |
|---|---|---|
| Language/runtime | Python 3.12 | `falkordb-py` and `langchain-falkordb` target ≥3.10 |
| API | FastAPI + Uvicorn | SSE for chat streaming |
| Orchestration | LangGraph | Pin the version range that `langchain-falkordb`'s `langgraph` extra supports (`>=0.6,<2` at the time of writing) |
| Graph | FalkorDB (`falkordb/falkordb` image includes Browser on :3000) | `falkordb-py` async client |
| LLM | Provider adapter over LangChain chat models (OpenAI / Anthropic / Gemini / Ollama), selected by env | Temperature 0. Structured output for extraction |
| Validation/config | Pydantic v2, pydantic-settings | – |
| Logging | structlog (JSON) with request id, tenant, handover id | – |
| Frontend | React 19 + React Router 7 + Vite 8 + TypeScript + Tailwind CSS 4 | Light theme built from the logo colours; TanStack Query for data fetching (planned) |
| Graph viz | **Cytoscape.js** | Better than React Flow for laid-out knowledge graphs; React Flow suits node editors |
| Quality | ruff (lint+format), mypy (strict), pytest; oxlint + `tsc`; Vitest (planned) | – |
| Packaging | `uv` (Python), `npm` (frontend) | – |
| Containers | Docker Compose: `falkordb`, `backend`, `frontend` | – |
| CI | GitHub Actions: lint, type-check, unit tests, query tests against a FalkorDB service container, benchmark smoke | – |

Deviations from the brief: none needed. Embeddings/vector index stay optional, so the MVP has no
embedding-provider dependency.

---

## R. Repository structure

Top level (fixed by the team):

```
handovers/
├── app/
│   ├── frontend/        React UI
│   └── backend/         FastAPI + LangGraph modular monolith
├── graph/               schema migrations, named Cypher queries, seed loader inputs, query tests
├── docs/                design notes (this folder)
├── scripts/             one-shot dev/ops scripts (seed, reset, benchmark, export)
├── deployment/          live hosting notes
├── docker-compose.yml   FalkorDB + backend + frontend (dev: stop the app containers, run them on the host)
├── website/             optional static landing page (last priority)
├── AGENTS.md            rules for humans and AI assistants working in the repo
├── README.md            judge-facing entry point
├── .env.example
├── .gitignore
└── LICENSE
```

Planned internals:

```
app/backend/
  main.py              # FastAPI app; run with `uv run uvicorn main:app --reload`
  core/                # config, logging, FalkorDB client
  api/                 # FastAPI routers + request/response schemas
  services/            # handover use cases + pure rules (gap priority, projection, confidence)
  agents/              # LangGraph graphs: orchestrator, interview, personal memory agent; tools
  tests/ unit/ integration/ e2e/
graph/
  migrations/          # 0001_indexes.cypher, 0002_constraints.txt (GRAPH.CONSTRAINT commands)
  queries/             # one .cypher file per named query (Q1…Q23), loaded by the repo layer
  seed/                # synthetic company as connector-shaped JSON events
  benchmark/           # questions, gold answers, gold memory ids, seeded-gap list
app/frontend/
  src/ app/ layouts/ pages/ components/(ui/) hooks/ lib/ types/ styles/
```

Rules: keep pure logic (scoring, policies) free of I/O so it is unit-testable; only `core/` talks to FalkorDB. Cypher lives in
`graph/queries/*.cypher` (never inline f-strings) and always takes parameters, which also makes
every query reviewable by judges.

---

## Q. Data ingestion

```
Source fixture (JSON, connector-shaped: github/jira/slack/docs/pager/calendar)
 → Connector (reads fixture; later: real API)
 → Normalizer → Event {event_id, system, type, occurred_at, actor_id, payload}
 → Entity resolution (ids are stable in fixtures; real connectors would need matching rules)
 → Relationship extraction (deterministic mapping per event type)
 → Memory classification (episodic: event; semantic/procedural: knowledge items declared in fixtures)
 → Temporal resolution (valid_from from occurred_at/merged_at; supersession declared or detected)
 → Provenance (EVIDENCED_BY, AUTHORED_BY, quality prior)
 → FalkorDB (MERGE by id; idempotent; one transaction per event)
 → Memory attribution: agent of each participant gets a Memory (observed) — author, resolver, attendees
```

Memory attribution is the rule that makes "who knows what" computable. A person's agent remembers
what they authored, resolved, reviewed or attended. It does not remember everything they could read.

Only interview answers go through LLM extraction.

---

## S. API design (REST, JSON)

Identity is sent as a header `X-Demo-User: emp:priya` (demo only). Tenant comes from server config.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/employees` · `/api/employees/{id}` | directory + agent id |
| GET | `/api/employees/{id}/knowledge` | Q1 (manager/self) |
| GET | `/api/risk` | betweenness + per-service unique-knowledge counts |
| POST | `/api/handovers` | open `{employee_id, successor_id, trigger, effective_at}` |
| GET | `/api/handovers/{id}` | state, responsibilities, at-risk, gaps, transfer |
| POST | `/api/handovers/{id}/analyze` | run analysis (async; status polled) |
| GET | `/api/handovers/{id}/gaps` | gaps with priority |
| POST | `/api/handovers/{id}/interview/sessions` | start/resume interview session |
| POST | `/api/interview/sessions/{sid}/messages` | answer (SSE response) |
| POST | `/api/handovers/{id}/review` | employee confirm/edit/private per item |
| GET | `/api/handovers/{id}/projection` | included/excluded with reasons |
| POST | `/api/handovers/{id}/approvals` | manager approve/reject (batch or items) |
| POST | `/api/handovers/{id}/transfer` | apply (idempotent) |
| POST | `/api/transfers/{id}/revoke` | revoke |
| POST | `/api/agents/{agent_id}/sessions` | start Q&A session |
| POST | `/api/sessions/{sid}/ask` | ask (SSE): answer, citations, as_of |
| GET | `/api/turns/{turn_id}/provenance` | Q12 path JSON for Cytoscape |
| GET | `/api/memories/{id}/lineage` | Q11 |
| GET | `/api/audit?handover_id=` | audit events |
| GET | `/api/queries` | catalogue of named Cypher queries (judge transparency) |
| GET | `/healthz` · `/readyz` | liveness / FalkorDB reachable |

Errors use a uniform `{error: {code, message, details}}` body. State conflicts return 409, and
authorisation failures return 403.

---

## T. Frontend information architecture

| Route | Persona | Content |
|---|---|---|
| `/` | Manager | Org risk: services by unique-knowledge count; bottleneck people (Q20); open handovers |
| `/people/:id` | Manager/self | Agent memory inventory by type; responsibilities |
| `/handovers/:id` | Manager | Stepper (state machine), responsibilities, at-risk list, gaps by priority |
| `/handovers/:id/interview` | Departing employee | One gap at a time, chat, proposed knowledge cards to confirm |
| `/handovers/:id/review` | Employee then manager | Included/excluded with reasons; private toggle; approve |
| `/agents/:id/chat` | Successor | Chat; right panel: citations, "why you know this", path graph, as-of |
| `/lineage/:memoryId` | Compliance | Lineage chain, approvals, revoke |
| `/graph` | Judges | Cytoscape view of a handover's subgraph + "show Cypher" drawer |

A persona switcher in the header sets `X-Demo-User`.

---

## W. Testing strategy

| Layer | What | How |
|---|---|---|
| Domain unit | scoring, priority, projection filters, confidence (noisy-OR), state machine transitions | pytest, no I/O |
| Query tests | each `graph/queries/*.cypher` against a fresh seeded graph; exact expected rows | pytest + FalkorDB service; graph reset via `GRAPH.DELETE` + seed, or `GRAPH.COPY` from a pristine seeded graph |
| Integration | use cases with real FalkorDB, fake LLM (deterministic stub) | pytest |
| Agent | tool-call contracts; abstention when `not_held`; citation validator | fake LLM scripted responses |
| API | routers with test client | pytest |
| Frontend | components with mocked API; type-check | Vitest, `tsc` |
| E2E | the demo script end-to-end via API | pytest, run in CI on fixtures |
| Benchmark | `app/backend/bench/` (see the root README) | results committed in `graph/benchmark/results/` |

## X. Deployment

- **Local (required):** `docker compose up -d --build` from the repo root, then seed. For dev,
  `docker compose stop backend frontend` and run both on the host with live reload.
  FalkorDB (`falkordb/falkordb:6.0.1`) exposes 6379 (Redis protocol) and 3000 (Browser).
  Persistence uses the image's data path `/var/lib/falkordb/data` (a named volume) with
  `--appendonly yes`, following the FalkorDB Docker guide
  ([docs](https://docs.falkordb.com/operations/docker)). Set the password through `REDIS_ARGS=--requirepass …`.
- **Live:** one small VM running the same Compose file behind Caddy (TLS); see
  [deployment/](../deployment/README.md).
- Secrets only via env. `.env.example` lists every variable without values.
