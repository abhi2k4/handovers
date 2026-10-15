# app/backend/seed/

The synthetic sample company, Northwind (no real people or data).

| Module | Run | What |
|---|---|---|
| `generate.py` | `uv run python -m seed.generate` | Writes `graph/seed/northwind/` as connector-shaped fixtures |
| `load.py` | `uv run python -m seed.load [--reset]` | Applies `graph/schema/indexes.cypher` and loads the fixtures (also used at startup with `SEED_ON_START=true`) |
| `samples.py` | `uv run python -m seed.samples` | Writes sample upload files to `graph/seed/northwind/samples/` |
