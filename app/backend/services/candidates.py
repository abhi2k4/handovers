"""Candidates from a job board's CSV export (WorkIndia has no API), screened per criterion.

Each candidate gets the screening kit's verdicts (meets / missing / unclear) and a count of
must-haves found. There is deliberately no overall score or ranking (see generators.check_resume).
"""

import csv
import io
import json
import re
from typing import Any

from services.generators import check_resume_rules

NAME = ("name", "full name", "fullname", "candidate name", "candidate")
PHONE = ("mobile", "phone", "phone number", "mobile number", "contact")
CITY = ("city", "location", "locality")


def _pick(row: dict[str, str], keys: tuple[str, ...]) -> str:
    return next((row[k].strip() for k in keys if row.get(k)), "")


def parse(text: str) -> list[dict[str, str]]:
    """Rows with name, phone, city and everything else as one summary (column: value; ...)."""
    out = []
    for raw in csv.DictReader(io.StringIO(text.strip())):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        name = _pick(row, NAME)
        if not name:
            continue
        used = set(NAME + PHONE + CITY)
        summary = "; ".join(f"{k.capitalize()}: {v}" for k, v in row.items() if k not in used and v)
        phone = re.sub(r"\D", "", _pick(row, PHONE))
        out.append({"name": name, "phone": phone, "city": _pick(row, CITY), "summary": summary})
    return out


def screen(
    rows: list[dict[str, str]], criteria: list[dict[str, Any]], hid: str, source: str
) -> list[dict[str, Any]]:
    must = [c for c in criteria if c["level"] == "must"]
    out = []
    for r in rows:
        verdicts = check_resume_rules(r["summary"], criteria)
        met = sum(1 for v in verdicts if v["level"] == "must" and v["verdict"] == "meets")
        out.append(
            r
            | {
                "id": f"{hid}|{r['phone'] or r['name'].lower()}",
                "source": source,
                "must_met": met,
                "must_total": len(must),
                "verdicts": json.dumps(verdicts),
            }
        )
    return out
