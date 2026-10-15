# graph/project/

The project graph: how Handovers itself is built, stored in FalkorDB so the app can explain itself.
Judges open it from the sidebar: **How it's built**.

| File | What |
|---|---|
| `architecture.json` | Components (`id`, `name`, `kind`, `summary`, `path` in this repo) and links (`[from, to, how]`) |

**How it flows.** At backend startup `services/tech_graph.py` hashes `architecture.json` and, if the
hash differs from the one stored on the graph's `ProjectMeta` node, rebuilds the FalkorDB graph
`handovers_project` with `project_clear` and `project_load` (both in `graph/queries/`). The view
calls `GET /api/xray/project`, which runs one read-only named query, `project_graph`, and also shows
that Cypher in its **Cypher** tab. The graph is separate from the company graphs
(`handovers__<tenant>`), and its name cannot collide with one.

**Model.** `(:Component {id, name, kind, summary, path})-[:USES {how}]->(:Component)`, plus one
`(:ProjectMeta {version})`. `kind` is one of `client`, `frontend`, `api`, `service`, `core`,
`graph`, `store`, `connector`, `identity`, `external`; the view lays the kinds out left to right in
that order, the way a request travels.

**Changing it.** Edit `architecture.json` in the same commit as the architecture change. Every link
must name existing components and every component must be linked:
`tests/unit/test_tech_graph.py` checks both. Restart the backend and the graph reloads.
