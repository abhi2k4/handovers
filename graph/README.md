# graph/

Everything that defines and exercises the FalkorDB graph: the core of Handovers.

| Path | Contents |
|---|---|
| `schema/indexes.cypher` | Range and full-text indexes, applied by `python -m seed.load` (idempotent) |
| `queries/` | One parameterised `.cypher` file per named query, loaded by the backend by name |
| `seed/northwind/` | Synthetic company: `org.json`, `sources.jsonl` (441 work records with their extracted facts), `interview.json` (scripted exit-interview answers), `benchmark.json`, `samples/` (files to try in the upload screen) |
| `seed/interview_bank.json` | Interview questions per skill for the interview kit |
| `benchmark/results/` | Committed benchmark runs (`python -m bench.run`) |
| `project/architecture.json` | How Handovers itself is built (components and links). Loaded into its own FalkorDB graph, `handovers_project`, at startup and shown by the app's **How it's built** button ([project/README.md](project/README.md)) |

Regenerate the sample company: `uv run python -m seed.generate` (and `seed.samples`) in `app/backend`.
Design: [`../docs/graph-model.md`](../docs/graph-model.md). Data model and key queries: root [README](../README.md#graph-data-model).
