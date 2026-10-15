# graph/queries/

Every Cypher query the app runs, one file each, loaded by name (`core/graph.py`). Rules:

- **Parameterised** (`$name`), never built from user input.
- **Reads run with `GRAPH.RO_QUERY`** (`Graph.read`); writes with `Graph.run`.
- **The first comment line says what it returns**; the Graph X-ray and the query catalogue show it.
- A query change comes with a test against the seeded graph.

Files are grouped by prefix: `person_*`, `handover_*`, `gap_*`, `transfer_*`, `knowledge_*`,
`fact_*`, `review_*`, `org_*`, `dash_*`, `risk_*`, `ramp_*`, `companion_*`, `connector_*`,
`session_*`, `operator_*`, `project_*` (the project graph, not a company graph), and a few singles.
