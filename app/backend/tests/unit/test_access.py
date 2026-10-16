"""Access rules (docs/product-strategy.md section 10.1). Pure: no graph needed."""

from dataclasses import replace

from services.access import (
    Caller,
    _current,
    can_act_as,
    can_answer,
    can_approve,
    can_assign_backup,
    can_configure,
    can_read_answers,
    can_reassign_account,
    can_run_handover,
    can_view_handover,
    can_view_org,
    can_view_person,
    can_view_setup,
    hide_private,
    platform_admin,
    redact_excluded,
    redact_gaps,
    redact_person,
    roles_for,
)

LEAVER = "emp:nisha"


def caller(
    cid: str, roles: set[str], reports: set[str] = frozenset(), **kw: tuple[str, ...]
) -> Caller:  # type: ignore[assignment]
    return Caller(
        id=cid,
        name=cid,
        title="",
        team=None,
        roles=frozenset(roles | {"employee"}),
        reports=frozenset(reports),
        **kw,
    )


HR = caller("emp:meera", {"hr", "it"})
MANAGER = caller("emp:aditi", {"manager"}, {LEAVER})
LEAVING = caller(LEAVER, set(), leaving=("ho:1",))
SUCCESSOR = caller("emp:ananya", set(), succeeding=("ho:1",))
EXEC = caller("emp:kavya", {"exec"})
OTHER = caller("emp:arjun", set())


def test_roles_from_team_and_title() -> None:
    assert roles_for("team:people", "HR & Admin Lead") >= {"hr", "it", "employee"}
    assert "exec" in roles_for("team:leadership", "Founder & CEO")
    assert roles_for("team:growth", "Performance Marketer") == {"employee"}


def test_hr_runs_the_process_but_cannot_read_or_approve() -> None:
    assert can_run_handover(HR, LEAVER)
    assert can_view_handover(HR, LEAVER)
    assert not can_read_answers(HR, LEAVER)
    assert not can_approve(HR, LEAVER)


def test_only_the_manager_approves() -> None:
    assert can_approve(MANAGER, LEAVER)
    for who in (HR, LEAVING, SUCCESSOR, EXEC, OTHER):
        assert not can_approve(who, LEAVER)


def test_only_the_leaver_answers_and_never_sees_hiring() -> None:
    assert can_answer(LEAVING, LEAVER)
    assert not can_answer(MANAGER, LEAVER)
    assert not can_run_handover(LEAVING, LEAVER)


def test_people_act_only_as_themselves() -> None:
    assert can_act_as(SUCCESSOR, "emp:ananya")
    assert not can_act_as(SUCCESSOR, LEAVER)


def test_org_views_and_person_views() -> None:
    assert can_view_org(HR) and can_view_org(EXEC)
    assert not can_view_org(MANAGER) and not can_view_org(OTHER)
    assert can_view_person(MANAGER, LEAVER) and can_view_person(OTHER, "emp:arjun")
    assert not can_view_person(OTHER, LEAVER)


def test_no_caller_means_unrestricted() -> None:
    assert can_approve(None, LEAVER) and can_read_answers(None, LEAVER) and can_view_org(None)


def test_home_screen_per_role() -> None:
    assert LEAVING.home == "leaver"
    assert SUCCESSOR.home == "successor"
    assert HR.home == "overview" and EXEC.home == "leadership"
    # A CEO with direct reports still lands on the leadership home, not the manager's.
    assert (
        replace(EXEC, roles=EXEC.roles | {"manager"}, reports=frozenset({"emp:aditi"})).home
        == "leadership"
    )
    assert MANAGER.home == "manager"
    assert OTHER.home == "employee"
    assert platform_admin().home == "platform"


def test_the_platform_admin_sees_no_people_or_handover_content() -> None:
    admin = platform_admin()
    assert not can_view_org(admin)
    assert not can_view_handover(admin, "emp:leaver")
    assert not can_read_answers(admin, "emp:leaver")
    assert not can_run_handover(admin, "emp:leaver")


def test_redaction_keeps_progress_drops_content() -> None:
    gaps = [
        {
            "id": "g1",
            "rule": "G1",
            "label": "No recorded reason",
            "status": "answered",
            "title": "CAC target is 900",
            "answer": "Because...",
            "context": "deck",
        }
    ]
    gaps.append(
        {
            "id": "g2",
            "rule": "G7A",
            "label": "Only admin",
            "status": "open",
            "title": "Mixpanel workspace",
            "target_kind": "Account",
        }
    )
    out, account = redact_gaps(gaps)
    assert out["status"] == "answered" and out["title"] == "No recorded reason"
    assert account["title"] == "Mixpanel workspace"
    assert "answer" not in out and "context" not in out
    person = redact_person({"id": "x", "knowledge": [{"id": "k1"}, {"id": "k2"}]})
    assert person["knowledge"] == [] and person["knowledge_count"] == 2


def test_others_never_see_private_or_personal_items() -> None:
    person = {
        "knowledge": [
            {"id": "k1", "private": False, "sensitivity": "internal"},
            {"id": "k2", "private": True, "sensitivity": "internal"},
            {"id": "k3", "private": False, "sensitivity": "personal"},
        ],
        "recent": [
            {"id": "s1", "sensitivity": "internal"},
            {"id": "s2", "sensitivity": "personal"},
        ],
    }
    out = hide_private(person)
    assert [k["id"] for k in out["knowledge"]] == ["k1"]
    assert [s["id"] for s in out["recent"]] == ["s1"]


def test_manager_sees_that_private_items_stay_not_what_they_are() -> None:
    preview = {
        "exclude": [
            {"id": "k1", "title": "Salary notes", "reason": "personal"},
            {"id": "k2", "title": "Old pricing", "reason": "superseded"},
        ]
    }
    out = redact_excluded(preview)["exclude"]
    assert [x["title"] for x in out] == ["Private item", "Old pricing"]
    assert out[0]["id"] == "private:0" and out[1]["id"] == "k2"


def test_it_hr_and_the_manager_reassign_accounts() -> None:
    assert can_reassign_account(HR, LEAVER)
    assert can_reassign_account(MANAGER, LEAVER)
    assert not can_reassign_account(LEAVING, LEAVER)
    assert not can_reassign_account(OTHER, LEAVER)


def test_managers_pick_backups_from_their_own_team() -> None:
    assert can_assign_backup(HR, [LEAVER], "emp:arjun")
    assert can_assign_backup(MANAGER, [LEAVER], LEAVER)  # a teammate of the owner
    assert can_assign_backup(MANAGER, [LEAVER], "emp:aditi")  # themselves
    assert not can_assign_backup(MANAGER, [LEAVER], "emp:arjun")  # outside the team
    assert not can_assign_backup(MANAGER, ["emp:arjun"], LEAVER)  # not their owner
    assert not can_assign_backup(OTHER, [LEAVER], "emp:arjun")


def test_transferred_handovers_stay_in_context_cancelled_ones_drop() -> None:
    rows = [
        {"id": "ho:a", "status": "transferred"},
        {"id": "ho:b", "status": "cancelled"},
        {"id": "ho:c", "status": "open"},
    ]
    assert _current(rows) == ("ho:a", "ho:c")


def test_only_the_platform_admin_configures_the_organisation() -> None:
    assert can_configure(platform_admin())
    assert can_configure(None)
    # A demo guest viewing as the platform admin may look, never change.
    guest = replace(platform_admin(), guest=True)
    assert can_view_setup(guest) and not can_configure(guest)
    assert not can_view_setup(HR)
    assert not can_configure(HR)
    assert not can_configure(MANAGER)
    assert not can_configure(EXEC)
    assert not can_configure(OTHER)


def test_approver_falls_back_up_the_chain_then_to_hr() -> None:
    from services.access import pick_approver

    manager = {"id": "emp:aditi", "name": "Aditi", "status": "active", "depth": 1, "leaving": False}
    boss = {"id": "emp:kavya", "name": "Kavya", "status": "active", "depth": 2, "leaving": False}
    assert pick_approver([manager, boss])["id"] == "emp:aditi"
    leaving = manager | {"leaving": True}
    assert pick_approver([leaving, boss]) | {} == {
        "id": "emp:kavya",
        "name": "Kavya",
        "via": "skip-level manager",
    }
    assert pick_approver([manager | {"status": "departed"}])["via"] == "hr"
    assert pick_approver([])["via"] == "hr"  # e.g. the CEO


def test_only_the_approver_approves_and_hr_still_cannot_read_answers() -> None:
    from services.access import (
        can_approve,
        can_ask_question,
        can_dismiss_question,
        can_read_answers,
    )

    skip = Caller(
        id="emp:kavya",
        name="",
        title="",
        team=None,
        roles=frozenset({"employee"}),
        approves=frozenset({LEAVER}),
    )
    away = Caller(
        id="emp:aditi",
        name="",
        title="",
        team=None,
        roles=frozenset({"manager"}),
        reports=frozenset({LEAVER}),
        approves=frozenset(),
    )
    hr_fallback = Caller(
        id="emp:meera",
        name="",
        title="",
        team=None,
        roles=frozenset({"hr"}),
        approves=frozenset({LEAVER}),
    )
    assert can_approve(skip, LEAVER) and can_read_answers(skip, LEAVER)
    assert not can_approve(away, LEAVER)  # leaving too: the next one up approves
    assert can_approve(hr_fallback, LEAVER) and not can_read_answers(hr_fallback, LEAVER)
    # Questions: HR and the manager add them; only the manager drops them, never mandatory ones.
    assert can_ask_question(HR, LEAVER) and can_ask_question(MANAGER, LEAVER)
    assert can_dismiss_question(MANAGER, LEAVER, False)
    assert not can_dismiss_question(MANAGER, LEAVER, True)
    assert not can_dismiss_question(HR, LEAVER, False)
    leaver = Caller(id=LEAVER, name="", title="", team=None, roles=frozenset({"employee"}))
    assert not can_dismiss_question(leaver, LEAVER, False)
