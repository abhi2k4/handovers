# app/backend/api/

HTTP routers: one module per area. A router checks *who may* (`services/access.py`), calls a
service, and returns JSON. No Cypher and no business rules here.

| Module | Prefix | What |
|---|---|---|
| `deps.py` | | Shared dependencies: the graph, the LLM, and the caller (session cookie, else the View-as header for guests) |
| `health.py` | `/healthz`, `/readyz`, `/api/status` | Liveness, readiness (FalkorDB reachable), UI status |
| `auth.py` | `/api/auth` | Sign-in (Backend-for-Frontend with Keycloak), session, sign-out, sign-in providers, sync people |
| `me.py` | `/api` | Who am I, demo personas, KPIs, the copilot search bar |
| `people.py` | `/api/people` | People and their work memory, scoped to the caller |
| `handovers.py` | `/api/handovers` | Open, outputs, exit interview, transfer |
| `readiness.py` | `/api/handovers/{id}/readiness`, `/api/responsibilities/{id}/backup` | Last-day readiness, account reassignment, backup owners |
| `ramp.py` | `/api/handovers/{id}/ramp` | The successor's ramp-up plan |
| `companion.py` | `/api/companion` | The successor asks the leaver's memory |
| `uploads.py` | `/api` | Upload a document; the review queue |
| `alerts.py` | `/api/alerts`, `/api/whatsapp/webhook` | Alert settings, inbox, reminders, digest, the platform admin's WhatsApp channel (`/api/alerts/delivery`), Meta's webhook |
| `candidates.py` | `/api` | Candidates for a leaver's vacancy: import, screen, alert |
| `connectors.py` | `/api/connectors` | Integrations: list, connect, test, sync (platform admin) |
| `xray.py` | `/api/xray` | Query traces, the subgraph around a subject, the project graph |
| `meta.py` | `/api` | App metadata, the query catalogue, demo answers and reset |

Adding a route: put it in the router for its area (or a new module registered in `main.py`), gate
it with a rule from `services/access.py`, keep the work in a service, and add a test.
