"""Alert routing and messages (pure)."""

import json

from services.alerts import digest_text, hour_ist, is_quiet, reminder, route

TEN_AM_IST = 1_791_779_400_000  # 2026-10-12 10:00 IST
NIGHT = TEN_AM_IST + 13 * 3_600_000  # 23:00 IST


def test_quiet_hours_wrap_midnight() -> None:
    assert hour_ist(TEN_AM_IST) == 10
    assert is_quiet(23, 21, 9) and is_quiet(3, 21, 9) and not is_quiet(10, 21, 9)
    assert not is_quiet(10, 9, 9)


def test_route_by_mode_number_and_quiet_hours() -> None:
    s = {"phone": "919876543210", "quiet_from": 21, "quiet_to": 9}
    assert route("reminder", s, TEN_AM_IST, True) == "whatsapp"
    assert route("reminder", s, TEN_AM_IST, False) == "app"
    assert route("reminder", s | {"phone": ""}, TEN_AM_IST, True) == "app"
    assert route("reminder", s, NIGHT, True) == "held"
    assert route("lastday", s, NIGHT, True) == "whatsapp"  # critical
    assert (
        route("reminder", s | {"modes": json.dumps({"reminder": "off"})}, TEN_AM_IST, True) == "off"
    )
    assert (
        route("reminder", s | {"modes": json.dumps({"reminder": "digest"})}, TEN_AM_IST, True)
        == "digest"
    )


def test_transfer_reminder_asks_the_manager_to_approve() -> None:
    item = {"key": "transfer", "label": "Knowledge transfer approved", "detail": "", "href": "/h"}
    msg = reminder(item, {"id": "ho:1", "employee": "Nisha Verma"}, "Meera", 22)
    assert msg["kind"] == "approval" and msg["buttons"][0]["id"] == "approve:ho:1"
    assert "Nisha" in msg["title"] and "in 22 days" in msg["body"]


def test_digest_leads_with_numbers() -> None:
    hs = [
        {"status": "open", "ready": False, "days_left": 5, "employee": "Nisha Verma"},
        {"status": "transferred", "ready": True, "days_left": 0, "employee": "Arjun Mehta"},
    ]
    _, body = digest_text(hs, 2)
    assert body.startswith("Exits: 1 in progress · 1 at risk · next last day: Nisha, in 5 days")
    assert "2 alerts waiting" in body


def test_quiet_hours_hold_email_too_not_only_whatsapp() -> None:
    from services.alerts import route

    s = {"phone": "", "email": True, "modes": None, "quiet_from": 21, "quiet_to": 9}
    assert route("reminder", s, 0, False, hour=23, email_on=True) == "held"
    assert route("reminder", s, 0, False, hour=11, email_on=True) == "app"
    assert route("lastday", s, 0, False, hour=23, email_on=True) == "app"  # critical
    assert route("reminder", s, 0, False, hour=23, email_on=False) == "app"  # in-app only
