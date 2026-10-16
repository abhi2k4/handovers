"""Clearance rows, graph-derived confirmation and the relieving letter (pure)."""

from services.clearance import counts, letter, rows, view

PERSON = {
    "accounts": [
        {"id": "acc:mixpanel", "name": "Mixpanel workspace", "role": "admin", "other_admins": []},
        {"id": "acc:ads", "name": "Google Ads account", "role": "admin", "other_admins": ["Aditi"]},
    ],
    "responsibilities": [
        {"id": "resp:utm", "title": "Rebuild the UTM sheet", "co_owners": []},
        {"id": "resp:ab", "title": "Run A/B tests", "co_owners": ["Tara"]},
    ],
}


def test_rows_come_from_accounts_work_and_standard_items() -> None:
    r = rows(PERSON, "ho:1")
    labels = [x["label"] for x in r]
    assert labels[0] == "Hand over admin of Mixpanel workspace"
    assert labels[1] == "Remove access to Google Ads account"
    assert "New owner for: Rebuild the UTM sheet" in labels
    assert not any("A/B" in label for label in labels)  # shared work needs no new owner
    assert [x["key"] for x in r[:3]] == ["admin:acc:mixpanel", "access:acc:ads", "work:resp:utm"]
    assert r[0]["id"] == "ho:1|admin:acc:mixpanel" and [x["ord"] for x in r] == list(range(len(r)))


def test_graph_resolved_rows_are_confirmed_by_handovers() -> None:
    items = [x | {"status": "open"} for x in rows(PERSON, "ho:1")]
    v = view(items, {"admin:acc:mixpanel": ["Ananya Pillai"]})
    assert v[0]["status"] == "confirmed" and v[0]["auto"] and v[0]["by"] == "Ananya Pillai"
    assert v[1]["status"] == "open" and counts(v) == (1, len(v))


def test_letter_states_the_handover_and_no_dues() -> None:
    h = {
        "employee": "Nisha Verma",
        "title": "Marketer",
        "team": "Growth",
        "successor": "Ananya Pillai",
        "effective_at": 1_793_680_200_000,
    }
    out = letter(h, "Northwind", {"name": "Meera Iyer", "title": "HR"}, 1_791_779_400_000)
    assert out["date"] == "12 October 2026" and "until 3 November 2026" in out["body"][0]
    assert "to Ananya Pillai" in out["body"][1] and "no dues" in out["body"][1]
