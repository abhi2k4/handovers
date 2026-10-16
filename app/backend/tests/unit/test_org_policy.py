"""The organisation's exit policy (pure parts)."""

from core.clock import DAY_MS
from services import jobs, letters, org_policy

P = org_policy.merge(None)


def test_hr_is_recognised_by_team_name_or_group_not_only_one_team_id() -> None:
    assert "hr" in org_policy.roles_for(P, "team:people", "People", "HR Lead")
    # A department synced from the directory as "Human Resources".
    assert "hr" in org_policy.roles_for(P, "team:human-resources", "Human Resources", "Generalist")
    assert org_policy.roles_for(P, "team:growth", "Growth", "Marketer") == {"employee"}
    p = org_policy.merge({"role_groups": {"IT Admins": "it", "Leadership Team": "exec"}})
    roles = org_policy.roles_for(
        p, "team:eng", "Engineering", "SRE", ["it admins", "Leadership Team"]
    )
    assert {"it", "exec"} <= roles and "hr" not in roles


def test_validate_catches_bad_settings() -> None:
    assert org_policy.validate(P) == []
    bad = P | {
        "withdrawal_days": -1,
        "timezone": "Mars/Base",
        "country_code": "+91",
        "role_groups": {"x": "admin"},
        "mandatory_questions": ["short"],
    }
    assert len(org_policy.validate(bad)) == 5


def test_times_and_phones_follow_the_organisation() -> None:
    ms = 1_760_250_000_000  # 2025-10-12 06:20 UTC
    assert org_policy.local_hour(P, ms) == 11  # IST
    assert org_policy.local_hour(org_policy.merge({"timezone": "Europe/London"}), ms) == 7
    nine = org_policy.next_local_hour(P, ms, 9)
    assert nine > ms and org_policy.local_hour(P, nine) == 9 and nine - ms < DAY_MS
    assert org_policy.phone(P, "98765 43210") == "919876543210"
    assert (
        org_policy.phone(org_policy.merge({"country_code": "44"}), "7700900123") == "447700900123"
    )
    assert org_policy.phone(P, "+44 7700 900123") == "447700900123"


def test_failed_jobs_retry_twice_then_stop() -> None:
    assert jobs.retry_at(0, 1) == jobs.RETRY_MS
    assert jobs.retry_at(0, 2) == 2 * jobs.RETRY_MS
    assert jobs.retry_at(0, 3) is None


def test_relieving_letter_waits_for_clearance_transfer_and_last_day() -> None:
    h = {"status": "interview", "effective_at": 10 * DAY_MS}
    assert "clearance" in letters.gate(h, False, P, 0)["reason"]
    assert "transfer" in letters.gate(h, True, P, 0)["reason"]
    done = h | {"status": "transferred"}
    early = letters.gate(done, True, P, 9 * DAY_MS)
    assert not early["can_send"] and early["ready_at"] == 10 * DAY_MS
    assert letters.gate(done, True, P, 10 * DAY_MS)["can_send"]
    assert letters.gate(done, True, P | {"letter_on_last_day": False}, 0)["can_send"]
    assert not letters.gate(done | {"letter_sent_at": 1}, True, P, 11 * DAY_MS)["can_send"]
