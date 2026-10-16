"""Job-board CSV import and per-criterion screening (pure)."""

import json

from services.candidates import parse, screen

CSV = """Name,Mobile,City,Experience,Skills
Kavita Joshi,90000 00104,Pune,5 years,"Meta Ads, GA4, ROAS"
,9000000000,Nowhere,1,"no name: skipped"
Arjun Nair,9000000105,Mumbai,1 year,Canva
"""
CRITERIA = [
    {"id": "s1", "label": "Hands-on Meta Ads Manager", "level": "must", "signals": ["meta ads"]},
    {"id": "s2", "label": "Hands-on GA4", "level": "must", "signals": ["ga4"]},
    {"id": "s3", "label": "Canva", "level": "nice", "signals": ["canva"]},
]


def test_parse_maps_columns_and_skips_rows_without_a_name() -> None:
    rows = parse(CSV)
    assert [r["name"] for r in rows] == ["Kavita Joshi", "Arjun Nair"]
    assert rows[0]["phone"] == "9000000104" and rows[0]["city"] == "Pune"
    assert rows[0]["summary"] == "Experience: 5 years; Skills: Meta Ads, GA4, ROAS"


def test_screen_counts_must_haves_without_a_score() -> None:
    out = screen(parse(CSV), CRITERIA, "ho:1", "WorkIndia")
    assert (out[0]["must_met"], out[0]["must_total"]) == (2, 2)
    assert (out[1]["must_met"], out[1]["must_total"]) == (0, 2)
    assert out[0]["id"] == "ho:1|9000000104" and "score" not in out[0]
    assert {v["verdict"] for v in json.loads(out[1]["verdicts"]) if v["level"] == "nice"} == {
        "meets"
    }
