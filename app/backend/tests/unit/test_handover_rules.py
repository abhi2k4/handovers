"""Rules for a handover's life (pure): successor, cancellation, questions, the days left."""

from zoneinfo import ZoneInfo

from core.clock import DAY_MS
from services import handover_rules as rules
from services import org_policy

NOW = 20_000 * DAY_MS
LEAVER = {"id": "emp:nisha", "team_id": "team:growth", "team": "Growth"}


def person(**extra: object) -> dict[str, object]:
    return {
        "id": "emp:ananya",
        "name": "Ananya",
        "status": "active",
        "team_id": "team:growth",
        "team": "Growth",
        "leaving": False,
    } | extra


def test_successor_cannot_be_the_leaver_someone_leaving_or_gone() -> None:
    assert rules.successor_problem(LEAVER, person()) is None
    for cand, code in [
        (person(id="emp:nisha"), "self"),
        (person(status="departed"), "departed"),
        (person(leaving=True), "leaving"),
        (None, "not_found"),
    ]:
        problem = rules.successor_problem(LEAVER, cand)
        assert problem and problem["code"] == code and problem["blocking"]


def test_successor_from_another_team_needs_confirmation_not_refusal() -> None:
    problem = rules.successor_problem(LEAVER, person(team_id="team:eng", team="Engineering"))
    assert problem and problem["code"] == "other_team" and not problem["blocking"]
    assert "Engineering" in problem["message"] and "Growth" in problem["message"]


def test_cancel_only_inside_the_withdrawal_window() -> None:
    p = org_policy.merge({"withdrawal_days": 7})
    h = {"status": "interview", "created_at": NOW, "effective_at": NOW + 30 * DAY_MS}
    assert rules.cancel_window(h, p, NOW + 3 * DAY_MS)["allowed"]
    late = rules.cancel_window(h, p, NOW + 8 * DAY_MS)
    assert not late["allowed"] and "7 days" in late["reason"]
    assert not rules.cancel_window(h | {"status": "transferred"}, p, NOW)["allowed"]
    assert not rules.cancel_window(h | {"status": "cancelled"}, p, NOW)["allowed"]
    # The window never runs past the last day.
    short = h | {"effective_at": NOW + 2 * DAY_MS}
    assert rules.cancel_window(short, p, NOW)["until"] == NOW + 2 * DAY_MS


def gap(i: int, rule: str, status: str = "open", priority: float = 0.5) -> dict[str, object]:
    return {"id": f"g{i}", "rule": rule, "status": status, "priority": priority, "title": f"q{i}"}


def test_mandatory_and_asked_questions_are_always_core_and_the_rest_are_extra() -> None:
    gaps = [gap(i, "G2", priority=0.6 - i / 100) for i in range(10)]
    gaps += [gap(20, "M"), gap(21, "Q"), gap(22, "G2", "dismissed"), gap(23, "G7R")]
    core, extra = rules.interview_sets(gaps, limit=3)
    ids = {g["id"] for g in core}
    assert {"g20", "g21"} <= ids and len(core) == 5
    assert {g["id"] for g in extra} == {f"g{i}" for i in range(3, 10)}
    assert "g22" not in ids | {g["id"] for g in extra}  # dismissed
    assert "g23" not in ids  # a plan item, not a question


def test_capture_plan_spreads_questions_and_ends_with_clearance() -> None:
    core = [gap(i, "G1") for i in range(6)]
    plan = rules.capture_plan(
        NOW,
        NOW + 5 * DAY_MS,
        ZoneInfo("Asia/Kolkata"),
        core,
        [gap(9, "G2")],
        [{"title": "Rebuild UTM sheet", "next_due": NOW + 2 * DAY_MS}],
        [{"name": "Rhea", "org": "PixelPine"}],
        [{"name": "Meta Business Manager"}],
        "Ananya Pillai",
    )
    assert plan["days_left"] == 5 and not plan["covered"] and plan["pace"] == 2
    kinds = [i["kind"] for d in plan["days"] for i in d["items"]]
    assert kinds.count("question") == 6 and "extra" in kinds and "intro" in kinds
    assert plan["days"][-1]["last"] and plan["days"][-1]["items"][-1]["kind"] == "exit"
    shadow = next(
        (d["offset"], i) for d in plan["days"] for i in d["items"] if i["kind"] == "shadow"
    )
    assert shadow[0] == 2 and "Ananya" in shadow[1]["title"]
    # Nothing in the last two days but access and clearance.
    assert all(
        i["kind"] in ("access", "exit")
        for d in plan["days"]
        if d["offset"] >= 4
        for i in d["items"]
    )


def test_capture_plan_keeps_going_once_everything_is_answered() -> None:
    plan = rules.capture_plan(
        NOW,
        NOW + 4 * DAY_MS,
        ZoneInfo("UTC"),
        [],
        [],
        [],
        [],
        [],
        None,
        [{"title": "Weekly budget pacing"}],
    )
    assert plan["covered"]
    assert any(i["kind"] == "walkthrough" for d in plan["days"] for i in d["items"])


def test_the_answer_decides_which_claim_is_current_not_its_age() -> None:
    choices = [{"id": "old", "value": "5"}, {"id": "new", "value": "3"}]
    assert rules.suggest_claim(choices, "3 is current. The runbook still says 5.") == "new"
    assert rules.suggest_claim(choices, "Honestly 5 is correct, the 3 was a test.") == "old"
    assert rules.suggest_claim(choices, "We changed it in 2025.") is None  # no bare "5" in "2025"
    rupees = [{"id": "q2", "value": "₹600"}, {"id": "jul", "value": "₹450"}]
    assert rules.suggest_claim(rupees, "₹450 is current. The deck shows ₹600.") == "jul"
