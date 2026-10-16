"""Handover readiness checklist (pure)."""

from core.clock import DAY_MS
from services.access import Caller
from services.readiness import build, for_caller

NOW = 1_000 * DAY_MS


def handover(**extra: object) -> dict[str, object]:
    return {
        "id": "ho:1",
        "employee": "Nisha Rao",
        "manager": "Aditi Sharma",
        "successor_id": "emp:ananya",
        "successor": "Ananya Iyer",
        "status": "open",
        "effective_at": NOW + 12 * DAY_MS,
        "gaps": [
            # Answering the "who takes over?" question does not move the account.
            {"rule": "G7A", "status": "answered"},
            {"rule": "G7A", "status": "dismissed", "resolution": "reassigned"},
            {"rule": "G1", "status": "answered"},
            {"rule": "G6", "status": "open"},
        ],
    } | extra


def test_lists_what_blocks_the_last_day_with_owners() -> None:
    r = build(handover(), set(), "draft", NOW)
    by = {i["key"]: i for i in r["items"]}
    assert r["days_left"] == 12 and not r["ready"]
    assert by["successor"]["done"] and by["successor"]["action"] is None
    assert not by["access"]["done"] and by["access"]["detail"] == "1 of 2 reassigned"
    assert by["access"]["owner"] == "IT"
    assert (
        by["interview"]["detail"] == "2 of 3 questions" and by["interview"]["owner"] == "Nisha Rao"
    )
    assert (
        by["ramp"]["detail"] == "Draft waiting for review" and by["ramp"]["owner"] == "Aditi Sharma"
    )
    assert r["done"] == 1 and r["total"] == 7


def test_ready_when_every_check_passes() -> None:
    gaps = [
        {"rule": "G7A", "status": "dismissed", "resolution": "reassigned"},
        {"rule": "G1", "status": "answered"},
    ]
    r = build(handover(gaps=gaps, status="transferred"), {"jd"}, "approved", NOW, 0, (12, 12))
    assert r["ready"] and r["done"] == r["total"]
    assert all(i["action"] is None for i in r["items"])


def test_no_questions_is_not_an_answered_interview() -> None:
    r = build(handover(gaps=[]), set(), None, NOW + 30 * DAY_MS)
    by = {i["key"]: i for i in r["items"]}
    assert not by["interview"]["done"] and r["days_left"] == 0
    assert by["ramp"]["detail"] == "Not created"


def test_actions_go_only_to_whoever_can_take_them() -> None:
    hr = Caller(id="emp:meera", name="", title="", team=None, roles=frozenset({"hr", "it"}))
    leaver = Caller(id="emp:nisha", name="", title="", team=None, roles=frozenset())
    r = build(handover(), set(), "draft", NOW)

    def mine(c: Caller) -> set[str]:
        return {i["key"] for i in for_caller(r, c, "emp:nisha")["items"] if i["mine"]}

    assert mine(hr) == {"access", "hiring", "clearance"}  # successor is already chosen
    assert mine(leaver) == {"interview"}
    assert all(i["short"] for i in r["items"])


def test_knowledge_captured_after_approval_reopens_the_transfer_check() -> None:
    r = build(handover(status="transferred"), set(), None, NOW, pending=2)
    t = next(i for i in r["items"] if i["key"] == "transfer")
    assert (
        not t["done"] and t["detail"] == "2 new since approval" and t["action"] == "Send new items"
    )


def test_pipeline_stage_is_the_first_unfinished() -> None:
    r = build(handover(), set(), "draft", NOW)
    assert r["stage"] == "capture"
    assert [s["state"] for s in r["stages"]] == ["done", "current", "todo", "todo", "todo"]
    r = build(handover(successor_id=None), set(), None, NOW)
    assert r["stage"] == "notice"


def test_pipeline_ends_ready_then_exited() -> None:
    done = handover(status="transferred", gaps=[{"rule": "G1", "status": "answered"}])
    r = build(done, {"jd"}, "approved", NOW, 0, (3, 3))
    assert r["ready"] and [s["state"] for s in r["stages"]][-1] == "current"
    r = build(done | {"effective_at": NOW}, {"jd"}, "approved", NOW, 0, (3, 3))
    assert all(s["state"] == "done" for s in r["stages"])


def test_clearance_gates_the_clearance_stage() -> None:
    done = handover(status="transferred", gaps=[{"rule": "G1", "status": "answered"}])
    r = build(done, {"jd"}, "approved", NOW, 0, (2, 3))
    by = {i["key"]: i for i in r["items"]}
    assert r["stage"] == "clearance" and by["clearance"]["detail"] == "2 of 3 confirmed"
