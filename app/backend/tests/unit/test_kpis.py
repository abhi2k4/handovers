"""Outcome KPIs are measured over completed handovers, never sample values. Pure: no graph needed."""

from services.kpis import outcomes

DAY = 86_400_000


def by_key(items: list[dict]) -> dict[str, dict]:  # type: ignore[type-arg]
    return {o["key"]: o for o in items}


def test_no_completed_handover_means_no_value() -> None:
    out = by_key(outcomes([], {}))
    assert set(out) == {"on_time", "knowledge_passed", "exit_answers", "accounts_closed"}
    assert all(o["value"] is None for o in out.values())
    assert all(o["detail"] == "No handover completed yet" for o in out.values())


def test_outcomes_count_on_time_knowledge_answers_and_accounts() -> None:
    rows = [
        {"id": "ho:a", "effective_at": 10 * DAY, "handed_at": 8 * DAY, "knowledge": 9},
        {"id": "ho:b", "effective_at": 10 * DAY, "handed_at": 11 * DAY, "knowledge": 3},
    ]
    gaps = {
        "ho:a": [
            {"rule": "G1", "status": "answered"},
            {"rule": "G6", "status": "open"},
            {"rule": "G1", "status": "dismissed"},  # dropped questions do not count
            {"rule": "G7A", "status": "dismissed"},  # reassigned
            {"rule": "G7A", "status": "open"},
        ],
        "ho:b": [{"rule": "G8", "status": "answered"}],
    }
    out = by_key(outcomes(rows, gaps))
    assert (
        out["on_time"]["value"] == 50 and out["on_time"]["detail"] == "1 of 2 completed handovers"
    )
    assert out["knowledge_passed"]["value"] == 12
    # Same questions as the handover page: G7A is asked too, unless reassigned (dismissed).
    assert out["exit_answers"]["value"] == 50  # 2 of 4
    assert out["accounts_closed"]["value"] == 50
