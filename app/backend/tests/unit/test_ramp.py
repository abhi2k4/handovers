"""Successor ramp-up plan: pure arrangement rules and access (product-strategy section 11)."""

from services.access import Caller, can_tick_ramp, can_view_ramp
from services.ramp import build_items

PERSON = {
    "name": "Nisha Verma",
    "manager_id": "emp:aditi",
    "accounts": [
        {"id": "acc:ga4", "name": "GA4", "other_admins": []},
        {"id": "acc:ads", "name": "Google Ads", "other_admins": ["Aditi Menon"]},
    ],
    "responsibilities": [
        {"id": "r:pacing", "title": "Budget pacing", "cadence": "daily", "co_owners": []},
        {"id": "r:meta", "title": "Meta Ads review", "cadence": "weekly", "co_owners": []},
        {"id": "r:report", "title": "Growth report", "cadence": "monthly", "co_owners": []},
        {"id": "r:lp", "title": "Landing page tests", "cadence": "biweekly", "co_owners": ["Tara"]},
    ],
    "knowledge": [
        {"id": "dec:reels", "kind": "Decision", "title": "Shift budget to Reels"},
        {"id": "clm:cac", "kind": "Claim", "title": "CAC target is 450"},
    ],
    "stakeholders": [
        {"id": "s:rhea", "name": "Rhea", "org": "Pixel & Pine", "other_contacts": []},
        {"id": "s:sam", "name": "Sam", "org": "Agency", "other_contacts": ["Aditi Menon"]},
    ],
}


def by_about() -> dict[str | None, dict[str, object]]:
    return {i["about"]: i for i in build_items(PERSON, "Aditi Menon")}


def test_items_come_only_from_graph_nodes_with_the_right_weeks() -> None:
    items = by_about()
    assert items["acc:ga4"]["week"] == 1 and items["acc:ga4"]["kind"] == "access"
    assert "acc:ads" not in items  # someone else is also admin
    assert items["r:pacing"]["week"] == 1
    assert items["r:meta"]["week"] == 2 and items["r:meta"]["kind"] == "shadow"
    assert items["r:report"]["week"] == 3 and items["r:report"]["kind"] == "own"
    assert items["r:lp"]["kind"] == "coordinate"  # shared work, whatever its cadence
    assert items["dec:reels"]["week"] == 1 and "clm:cac" not in items
    assert "s:rhea" in items and "s:sam" not in items
    assert items["emp:aditi"]["title"] == "1:1 with Aditi Menon"


def test_order_is_deterministic_and_numbered() -> None:
    first, second = build_items(PERSON, None), build_items(PERSON, None)
    assert [i["title"] for i in first] == [i["title"] for i in second]
    assert [i["ord"] for i in first] == list(range(len(first)))
    assert [i["week"] for i in first] == sorted(i["week"] for i in first)


def caller(cid: str, roles: set[str], reports: frozenset[str] = frozenset()) -> Caller:
    return Caller(
        id=cid,
        name=cid,
        title="",
        team=None,
        roles=frozenset(roles | {"employee"}),
        reports=reports,
    )


def test_who_sees_and_ticks_the_plan() -> None:
    manager = caller("emp:aditi", {"manager"}, frozenset({"emp:nisha"}))
    hr = caller("emp:meera", {"hr"})
    successor = caller("emp:ananya", set())
    assert can_view_ramp(manager, "emp:nisha", "emp:ananya", "draft")
    assert can_view_ramp(hr, "emp:nisha", "emp:ananya", "draft")
    assert not can_view_ramp(successor, "emp:nisha", "emp:ananya", "draft")
    assert can_view_ramp(successor, "emp:nisha", "emp:ananya", "approved")
    assert can_tick_ramp(successor, "emp:ananya") and not can_tick_ramp(manager, "emp:ananya")
