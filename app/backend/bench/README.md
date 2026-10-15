# app/backend/bench/

`run.py` (`uv run python -m bench.run`): can a successor get the right answer, from the right
source, without seeing private data? Deterministic and LLM-free, on its own tenant graph so the
demo is untouched. It compares four setups on the questions in
`graph/seed/northwind/benchmark.json` (before the handover, after it, flat full-text search, and a
naive copy of every memory) and writes `graph/benchmark/results/<date>.json`. No metric goes into
any doc unless it comes from a committed run.
