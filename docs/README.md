# docs/

Design notes for **Handovers**. The root [README](../README.md) is the overview; the code and the
named Cypher queries in [`../graph/queries/`](../graph/queries/) are the runnable truth.

| File | What's inside |
|---|---|
| [graph-model.md](graph-model.md) | FalkorDB schema: labels, relationships, properties, memory and time model, provenance, data boundaries, indexes |
| [architecture.md](architecture.md) | System, stack, repository layout, ingestion, API, frontend, testing, deployment |
| [handover-rules.md](handover-rules.md) | The business rules of an exit: successor, approvals, cancellation, mandatory questions, account handover, clearance, letter, background jobs, company policy |
| [product-strategy.md](product-strategy.md) | Audience, problems, roles, integrations, KPIs and the in-app user flow (§10) |
| [connectors.md](connectors.md) | Data connectors: one platform per kind of tool, how sync works, setup per platform |
| [identity-and-access.md](identity-and-access.md) | Keycloak sign-in, the role table (§0a), where secrets live (§0b) |
| [google-workspace-sso.md](google-workspace-sso.md) | Playbook: Google Workspace sign-in pinned to one domain, plus directory sync |

## Rules for this folder

- Every external claim links a source. Unverified items are marked **(unverified)**.
- No metrics until the benchmark has run and its results are committed.
- When implementation diverges from a doc, update the doc in the same commit.
