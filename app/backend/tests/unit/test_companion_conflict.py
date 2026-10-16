"""Companion: disagreeing live claims are shown together, never silently resolved."""

from services.companion import _latest_source, conflict_answer

DAY_MS = 86_400_000


def test_latest_source_names_daily_reports_by_kind_and_picks_the_newest() -> None:
    evidence = [
        {"id": "s1", "kind": "Document", "title": "Q2 growth plan (deck)", "at": 1775088000000},
        {"id": "s2", "kind": "EOD", "title": "EOD 09 Oct", "at": 1775088000000 + 190 * DAY_MS},
    ]
    assert _latest_source(evidence).startswith("Daily report, ")
    assert _latest_source([]) == ""


def test_conflict_answer_lists_every_value_with_its_source() -> None:
    top = {"title": "Blended CAC target is ₹450", "evidence": []}
    other = {
        "title": "Blended CAC target is ₹600",
        "evidence": [{"id": "s1", "kind": "Document", "title": "Q2 deck", "at": 1775088000000}],
    }
    text = conflict_answer(top, [other])
    assert text.startswith("Sources disagree: ")
    assert "₹450" in text and "₹600" in text and "(Q2 deck, " in text
    assert "exit interview" in text
