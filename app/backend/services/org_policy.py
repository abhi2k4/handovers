"""The organisation's exit policy: one versioned `Policy` node, edited by HR in the app.

Every company runs exits a little differently, so the rules that used to be hard-coded live here:
who counts as HR or leadership, how long a resignation can be withdrawn, the questions every leaver
answers, when the relieving letter may go out, and the organisation's time zone and phone prefix.
`DEFAULTS` describe the sample company; `merge` and the helpers below are pure and unit-tested.
"""

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from core.clock import now_ms
from core.graph import Graph

POLICY_ID = "policy:org"

DEFAULTS: dict[str, Any] = {
    # A resignation can be withdrawn this many days after the handover opens (and never after
    # the transfer is approved or the last day has passed).
    "withdrawal_days": 7,
    # The relieving letter goes out on the last day, not before.
    "letter_on_last_day": True,
    # Asked of every leaver, whatever the graph finds. Not dismissable.
    "mandatory_questions": [
        "What are you in the middle of right now, and what is the next step on each?",
        "Which dates or deadlines in the next three months will your successor need to know about?",
        "Where are the files, folders and dashboards you use most, and which of them only you can open?",
        "Who should your successor meet in their first week, and why?",
    ],
    # Who is HR: a team id or team/department name (synced from the directory), or a sign-in group.
    "hr_teams": [
        "team:people",
        "people",
        "human resources",
        "hr",
        "people operations",
        "hr & admin",
    ],
    # In small companies HR also administers accounts (the IT view). Off: IT comes from groups only.
    "hr_is_it": True,
    # Leadership is recognised from these words in a job title, or from a group mapped to `exec`.
    "exec_titles": ["ceo", "founder", "chief", "managing director"],
    # Sign-in (SSO) groups to roles, e.g. {"HR Business Partners": "hr", "IT Admins": "it"}.
    "role_groups": {},
    # Times (quiet hours, the digest, letter dates) and phone numbers.
    "timezone": "Asia/Kolkata",
    "country_code": "91",
    "digest_hour": 9,
}

ROLES = ("hr", "it", "exec")


def merge(saved: dict[str, Any] | None) -> dict[str, Any]:
    """Defaults overlaid with what the organisation saved; unknown keys are ignored."""
    out = dict(DEFAULTS)
    for key, value in (saved or {}).items():
        if key in DEFAULTS and value is not None:
            out[key] = value
    return out


def validate(p: dict[str, Any]) -> list[str]:
    """Problems with a policy an admin is about to save (empty = fine)."""
    problems = []
    if not isinstance(p.get("withdrawal_days"), int) or not 0 <= p["withdrawal_days"] <= 90:
        problems.append("Withdrawal window must be 0 to 90 days.")
    qs = p.get("mandatory_questions")
    if not isinstance(qs, list) or any(not isinstance(q, str) or len(q.strip()) < 8 for q in qs):
        problems.append("Each mandatory question needs at least a few words.")
    elif len(qs) > 12:
        problems.append("Keep mandatory questions to 12 or fewer.")
    try:
        ZoneInfo(str(p.get("timezone")))
    except (ZoneInfoNotFoundError, ValueError):
        problems.append(f"Unknown time zone: {p.get('timezone')}.")
    if not str(p.get("country_code", "")).isdigit():
        problems.append("Country code is digits only, e.g. 91 or 44.")
    if not isinstance(p.get("digest_hour"), int) or not 0 <= p["digest_hour"] <= 23:
        problems.append("Digest hour is 0 to 23.")
    bad = [r for r in (p.get("role_groups") or {}).values() if r not in ROLES]
    if bad:
        problems.append(f"Groups can map to {', '.join(ROLES)} only.")
    return problems


def _norm(values: list[str]) -> set[str]:
    return {v.strip().lower() for v in values if isinstance(v, str) and v.strip()}


def roles_for(
    p: dict[str, Any],
    team_id: str | None,
    team_name: str | None,
    title: str,
    groups: list[str] | None = None,
) -> frozenset[str]:
    """Job-function roles from the directory and sign-in groups (relationships add `manager`)."""
    roles = {"employee"}
    hr = _norm(p["hr_teams"])
    if (team_id or "").lower() in hr or (team_name or "").strip().lower() in hr:
        roles.add("hr")
        if p.get("hr_is_it"):
            roles.add("it")
    if any(word in title.lower() for word in _norm(p["exec_titles"])):
        roles.add("exec")
    mapping = {k.strip().lower(): v for k, v in (p.get("role_groups") or {}).items()}
    for g in groups or []:
        role = mapping.get(g.strip().lower())
        if role in ROLES:
            roles.add(role)
        if g.strip().lower() in hr:
            roles.add("hr")
    return frozenset(roles)


def zone(p: dict[str, Any]) -> ZoneInfo:
    try:
        return ZoneInfo(str(p.get("timezone") or DEFAULTS["timezone"]))
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(DEFAULTS["timezone"])


def local_hour(p: dict[str, Any], ms: int) -> int:
    return datetime.fromtimestamp(ms / 1000, zone(p)).hour


def next_local_hour(p: dict[str, Any], ms: int, hour: int) -> int:
    """The next time the clock in the organisation's zone shows `hour`:00, after `ms`."""
    tz = zone(p)
    here = datetime.fromtimestamp(ms / 1000, tz)
    at = here.replace(hour=hour, minute=0, second=0, microsecond=0)
    if at.timestamp() * 1000 <= ms:
        at = datetime.fromtimestamp(at.timestamp() + 86_400, tz).replace(
            hour=hour, minute=0, second=0, microsecond=0
        )
    return int(at.timestamp() * 1000)


def phone(p: dict[str, Any], raw: str) -> str:
    """Digits only, with the organisation's country code when a local number was typed."""
    digits = "".join(c for c in raw if c.isdigit())
    if raw.strip().startswith("+") or len(digits) > 10:
        return digits
    return (str(p.get("country_code") or "") + digits) if digits else ""


async def load(graph: Graph) -> dict[str, Any]:
    row = await graph.one("policy_get", {"id": POLICY_ID})
    saved = json.loads(row["rules_json"]) if row and row.get("rules_json") else {}
    return merge(saved) | {"version": (row or {}).get("version") or 0}


async def save(graph: Graph, p: dict[str, Any], by: str) -> dict[str, Any]:
    clean = merge(p)
    rows = await graph.run(
        "policy_save",
        {"id": POLICY_ID, "rules": json.dumps(clean), "by": by, "now": now_ms()},
    )
    return clean | {"version": rows[0]["version"] if rows else 1}
