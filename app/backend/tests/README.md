# app/backend/tests/

`uv run pytest -q` runs both folders.

| Folder | What |
|---|---|
| `unit/` | No I/O: access rules, policy, readiness, connectors and sign-in providers against recorded API responses (`httpx.MockTransport`), the architecture file |
| `integration/` | A real FalkorDB on throwaway graphs (`itest_*`), skipped when FalkorDB is not reachable (`docker compose up -d falkordb`) |

Behaviour changes come with a test; query changes come with one against the seeded graph.
