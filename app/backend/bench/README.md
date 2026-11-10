# app/backend/bench/

`run.py` (`uv run python -m bench.run`): can a successor get the right answer, from the right
source, without seeing private data? Deterministic and LLM-free, on its own tenant graph so the
demo is untouched. It compares four setups on the questions in
`graph/seed/northwind/benchmark.json` (before the handover, after it, flat full-text search, and a
naive copy of every memory) and writes `graph/benchmark/results/<date>.json`. No metric goes into
any doc unless it comes from a committed run.

**CI gate:** `uv run python -m bench.run --check` (same command in bash and PowerShell) runs the
benchmark, compares it with the newest file in `graph/benchmark/results/`, writes nothing, and fails
if the handover setup answers less often or less directly than that run, leaks anything private, or
knows anything before the handover. The `flat` comparison is not gated: full-text ties can come
back in a different order from run to run. After a change that improves the scores, commit a new run
(`uv run python -m bench.run`) so the gate holds the new level.
