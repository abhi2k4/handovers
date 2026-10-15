# app/backend/core/

Infrastructure every other package uses. Nothing here knows about handovers.

| Module | What |
|---|---|
| `config.py` | Settings from the environment and the root `.env` (pydantic-settings) |
| `falkordb.py` | The FalkorDB client; the tenant graph by default, or another named graph |
| `graph.py` | `QueryCatalog` (loads `graph/queries/*.cypher` by name) and `Graph` (runs them; reads use `GRAPH.RO_QUERY`; every call is traced) |
| `trace.py` | Records which named queries each request ran (Graph X-ray) |
| `llm.py` | Optional LLM adapter (Groq, Vertex, Anthropic); `none` means deterministic templates |
| `keycloak.py` | Sign-in: authorization code with PKCE, token checks, and the Keycloak admin API |
| `security.py` | Fernet encryption for stored credentials; session tokens and their hashes |
| `clock.py` | Epoch-millisecond time helpers; `OPEN` for open intervals |
| `logging.py` | Structured JSON logging (structlog), plain ASCII |
