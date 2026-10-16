"""Asking a whole memory (pure parts): intent, follow-ups, digest, overview, suggestions."""

from services import companion as c

PERSON = {
    "name": "Nisha Verma",
    "knowledge": [
        {
            "id": "dec:pause",
            "kind": "Decision",
            "title": "Pause all Google Ads campaigns",
            "others": [],
        },
        {
            "id": "proc:utm",
            "kind": "Procedure",
            "title": "Rebuild the UTM sheet",
            "steps": ["Export", "Map"],
            "others": ["Kabir"],
        },
        {
            "id": "k:1on1",
            "kind": "Claim",
            "title": "Career plans",
            "sensitivity": "personal",
            "others": [],
        },
        {
            "id": "clm:old",
            "kind": "Claim",
            "title": "CAC is 600",
            "status": "superseded",
            "others": [],
        },
    ],
    "responsibilities": [
        {
            "id": "resp:pacing",
            "title": "Track daily budget pacing",
            "cadence": "daily",
            "co_owners": [],
        }
    ],
    "stakeholders": [
        {
            "id": "sth:rhea",
            "name": "Rhea Sethi",
            "org": "Pixel & Pine",
            "context": "Agency lead",
            "other_contacts": [],
        }
    ],
    "accounts": [
        {"id": "acc:meta", "name": "Meta Business Manager", "role": "admin", "other_admins": []}
    ],
}


def test_overview_and_follow_up_intent() -> None:
    for q in ["whats in my memory", "What do I know?", "summarise my work", "who do I work with"]:
        assert c.is_overview(q), q
    assert not c.is_overview("Why did we pause Google Ads?")
    assert c.is_follow_up("and why?") and c.is_follow_up("how?")
    assert not c.is_follow_up("How do I rebuild the UTM sheet each month?")


def test_digest_keeps_personal_notes_and_replaced_claims_out() -> None:
    ids = {i["id"] for i in c.digest(PERSON)}
    assert ids == {"dec:pause", "proc:utm", "resp:pacing", "sth:rhea", "acc:meta"}
    only = {i["id"] for i in c.digest(PERSON) if i["only_you"]}
    assert "proc:utm" not in only and {"dec:pause", "acc:meta", "sth:rhea"} <= only


def test_overview_without_a_model_and_suggestions_from_the_memory() -> None:
    items = c.digest(PERSON)
    text = c.overview_answer("Nisha", items)
    assert text.startswith("Nisha's memory holds 5 items, 4 of them held by no one else")
    assert "- People (1): Rhea Sethi, Pixel & Pine" in text
    assert "empty" in c.overview_answer("Ananya", [])
    asks = c.suggestions(items)
    assert asks[0] == "What's in my memory?"
    assert "Why did we pause all Google Ads campaigns?" in asks
    assert any("Rhea Sethi" in q for q in asks) and "What do only I know?" in asks
    # An exit-interview answer that settled "sources disagree" is titled "Current: <claim>".
    settled = [{"kind": "Decision", "title": "Current: Blended CAC target is ₹450"}]
    assert "Why is “Blended CAC target is ₹450” current?" in c.suggestions(settled)


def test_graph_ids_are_stripped_from_answers() -> None:
    assert (
        c.clean("Pause all ads (dec:pause-google-ads), and Rhea (sth:rhea).")
        == "Pause all ads, and Rhea."
    )
