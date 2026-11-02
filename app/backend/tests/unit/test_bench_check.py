"""The CI benchmark gate: what counts as a regression against the committed run."""

from typing import Any

from bench.run import regressions


def run(answered: float, top1: float, leaks: int, before: float = 0.0) -> dict[str, Any]:
    return {
        "setups": {
            "handovers": {"answered_at_4": answered, "top1": top1, "leaks": leaks},
            "before": {"answered_at_4": before, "top1": 0.0, "leaks": 0},
        }
    }


COMMITTED = run(1.0, 1.0, 0)


def test_the_same_or_better_passes() -> None:
    assert regressions(run(1.0, 1.0, 0), COMMITTED) == []
    assert regressions(run(1.0, 1.0, 0), run(0.9, 0.8, 0)) == []


def test_fewer_answers_a_worse_first_hit_or_any_leak_fails() -> None:
    assert len(regressions(run(0.94, 1.0, 0), COMMITTED)) == 1
    assert len(regressions(run(1.0, 0.9, 0), COMMITTED)) == 1
    assert len(regressions(run(1.0, 1.0, 1), COMMITTED)) == 1


def test_knowing_things_before_the_handover_fails() -> None:
    assert len(regressions(run(1.0, 1.0, 0, before=0.1), COMMITTED)) == 1
