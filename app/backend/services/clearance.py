"""Exit clearance (no-dues): every account, piece of work and asset signed off before the letter.

Rows come from the leaver's graph (accounts they hold, work only they do) plus the standard admin
and finance rows. A row goes open -> done (its owner) -> confirmed (HR). Account and work rows
the graph already resolves (someone else holds the admin, owns the work) are confirmed by Handovers.
Pure, except `ensure` and `load`.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from core.clock import now_ms
from core.graph import Graph
from services import analysis

STANDARD = [
    ("asset:laptop", "Laptop and charger returned", "Admin"),
    ("asset:id", "ID card and keys returned", "Admin"),
    ("finance:dues", "No dues: advances and reimbursements settled", "Finance"),
    ("finance:fnf", "Full and final settlement sent to payroll", "Finance"),
]
STATUSES = ("open", "done", "confirmed")
IST = timezone(timedelta(hours=5, minutes=30))


def rows(person: dict[str, Any], hid: str) -> list[dict[str, Any]]:
    """`admin:` hand over a sole-admin account, `access:` remove access, `work:` new owner."""
    out: list[dict[str, Any]] = []
    for a in person.get("accounts") or []:
        if a["role"] in ("admin", "owner") and not a.get("other_admins"):
            key, label = f"admin:{a['id']}", f"Hand over admin of {a['name']}"
        else:
            key, label = f"access:{a['id']}", f"Remove access to {a['name']}"
        out.append(
            {"key": key, "label": label, "group": "Accounts", "owner": "IT", "target": a["id"]}
        )
    for r in person.get("responsibilities") or []:
        if not r.get("co_owners"):
            out.append(
                {
                    "key": f"work:{r['id']}",
                    "label": f"New owner for: {r['title']}",
                    "group": "Work",
                    "owner": "Manager",
                    "target": r["id"],
                }
            )
    for key, label, owner in STANDARD:
        out.append({"key": key, "label": label, "group": owner, "owner": owner, "target": ""})
    return [r | {"id": f"{hid}|{r['key']}", "ord": i} for i, r in enumerate(out)]


def view(items: list[dict[str, Any]], resolved: dict[str, list[str]]) -> list[dict[str, Any]]:
    """Rows the graph already resolves (`key -> new holders`) are confirmed by Handovers."""
    out = []
    for i in items:
        holders = resolved.get(i["key"])
        if holders:
            out.append(i | {"status": "confirmed", "by": ", ".join(holders), "auto": True})
        else:
            out.append(i | {"auto": False})
    return out


def counts(items: list[dict[str, Any]]) -> tuple[int, int]:
    return sum(1 for i in items if i["status"] == "confirmed"), len(items)


def letter(
    h: dict[str, Any], company: str, hr: dict[str, str], now: int, tz: Any = IST
) -> dict[str, Any]:
    """The relieving letter, from facts in the graph, dated in the organisation's time zone."""

    def day(ms: int | None) -> str:
        d = datetime.fromtimestamp((ms or now) / 1000, tz)
        return f"{d.day} {d.strftime('%B %Y')}"

    first = h["employee"].split(" ")[0]
    handed = f" to {h['successor']}" if h.get("successor") else ""
    return {
        "date": day(now),
        "to": h["employee"],
        "subject": "Relieving letter",
        "body": [
            f"This is to confirm that {h['employee']} worked with {company} as {h['title']} "
            f"in {h.get('team') or 'the company'} until {day(h.get('effective_at'))}.",
            f"Their resignation was accepted. They have completed all exit formalities, including "
            f"the handover of their work, accounts and contacts{handed}, and have no dues "
            f"outstanding with the company.",
            f"We thank {first} for their contribution and wish them well.",
        ],
        "signatory": hr,
    }


async def ensure(graph: Graph, hid: str, emp: str) -> None:
    person = await analysis.person(graph, emp)
    if person is not None:
        await graph.run(
            "clearance_ensure", {"handover": hid, "items": rows(person, hid), "now": now_ms()}
        )


async def load(graph: Graph, hid: str) -> list[dict[str, Any]]:
    items = await graph.read("clearance_list", {"handover": hid})
    rows_ = await graph.read("clearance_resolved", {"handover": hid, "now": now_ms()})
    return view(items, {r["key"]: r["holders"] for r in rows_})


async def tally(graph: Graph, hid: str) -> tuple[int, int]:
    return counts(await load(graph, hid))
