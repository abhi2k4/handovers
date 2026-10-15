"""Successor ramp-up plan (docs/product-strategy.md section 11).

Built entirely from the graph: what goes in the plan and how each item is worded (no LLM).

1. Gather: the leaver's work memory (`analysis.person`), without private or personal items.
2. Arrange (pure rules, `build_items`): week 1 access, daily work and decisions to read; week 2
   introductions and shadowing weekly work; weeks 3-4 owning monthly and shared work.
3. Word: fixed templates over each item's graph data (an LLM rewrite added nothing; see generate).
4. Store: RampPlan -FROM-> Handover, -FOR-> successor, -HAS_ITEM-> RampItem -ABOUT-> node.
"""

import uuid
from typing import Any

from core.clock import now_ms
from core.graph import Graph
from services import access, analysis

WEEKS = {1: "Week 1", 2: "Week 2", 3: "Weeks 3-4"}
DAILY = {"daily"}
SHORT = {"weekly", "biweekly"}


def build_items(person: dict[str, Any], manager: str | None) -> list[dict[str, Any]]:
    """Plan items from the leaver's work memory. Pure: no I/O, deterministic order."""
    leaver = (person.get("name") or "your predecessor").split()[0]
    items: list[dict[str, Any]] = []

    def add(week: int, kind: str, about: str | None, title: str, why: str) -> None:
        items.append({"week": week, "kind": kind, "about": about, "title": title, "why": why})

    for a in person.get("accounts") or []:
        if not a.get("other_admins"):
            add(
                1,
                "access",
                a["id"],
                f"Get admin access to {a['name']}",
                f"Only {leaver} administers it today; nobody can manage it after the last day.",
            )
    for r in person.get("responsibilities") or []:
        cadence = (r.get("cadence") or "").lower()
        shared = r.get("co_owners") or []
        if shared:
            add(
                3,
                "coordinate",
                r["id"],
                f"Agree who does what: {r['title']}",
                f"Shared with {', '.join(shared)}; settle the split early.",
            )
        elif cadence in DAILY:
            add(
                1,
                "take-over",
                r["id"],
                f"Take over: {r['title']}",
                f"{leaver} does this every day; it cannot pause.",
            )
        elif cadence in SHORT:
            add(
                2,
                "shadow",
                r["id"],
                f"Shadow one cycle, then run: {r['title']}",
                f"Runs {cadence}; one guided cycle is enough to take it over.",
            )
        else:
            add(
                3,
                "own",
                r["id"],
                f"Own end to end: {r['title']}",
                f"Runs {cadence or 'regularly'}; the next cycle falls in your first month.",
            )
    for k in person.get("knowledge") or []:
        if k.get("kind") == "Decision":
            add(
                1,
                "read",
                k["id"],
                f"Read the decision: {k['title']}",
                "Know why it was decided before changing anything it touches.",
            )
        elif k.get("kind") == "Procedure":
            add(
                3,
                "practise",
                k["id"],
                f"Practise: {k['title']}",
                "A written procedure; walk through it once before you need it.",
            )
    for s in person.get("stakeholders") or []:
        if not s.get("other_contacts"):
            add(
                2,
                "meet",
                s["id"],
                f"Meet {s['name']} ({s['org']})",
                f"Only {leaver} works with them; ask for an introduction before the last day.",
            )
    if manager:
        add(
            2,
            "meet",
            person.get("manager_id"),
            f"1:1 with {manager}",
            "Agree priorities for your first month.",
        )

    order = {
        "access": 0,
        "take-over": 1,
        "read": 2,
        "meet": 3,
        "shadow": 4,
        "own": 5,
        "coordinate": 6,
        "practise": 7,
    }
    items.sort(key=lambda i: (i["week"], order.get(i["kind"], 9), i["title"]))
    for n, item in enumerate(items):
        item["ord"] = n
        item["key"] = f"i{n}"
    return items


async def get(graph: Graph, hid: str) -> dict[str, Any] | None:
    plan = await graph.one("ramp_get", {"handover": hid})
    if plan is None:
        return None
    items = [i for i in plan["items"] if i.get("id") and not i.get("removed")]
    items.sort(key=lambda i: (i["week"], i["ord"]))
    done = sum(1 for i in items if i.get("done_at"))
    return {**plan, "items": items, "weeks": WEEKS, "done": done, "total": len(items)}


class NoSuccessor(Exception):
    pass


async def generate(graph: Graph, hid: str) -> dict[str, Any]:
    """Create the draft plan once; later calls return the existing plan."""
    existing = await get(graph, hid)
    if existing is not None:
        return existing
    h = await graph.one("handover_get", {"id": hid})
    if h is None or not h.get("successor_id"):
        raise NoSuccessor(hid)
    # After the transfer the leaver's work has moved: plan from what they held just before it.
    first = await graph.one("transfer_first_applied", {"handover": hid})
    at = first["at"] - 1 if first and first.get("at") else None
    person = await analysis.person(graph, h["employee_id"], at)
    if person is None:
        raise NoSuccessor(hid)
    items = build_items(access.hide_private(person), h.get("manager"))
    # Wording comes from fixed templates over graph data. An LLM rewrite was tried and dropped:
    # it echoed titles and added nothing the graph did not already say.
    method = "graph"
    plan_id = f"ramp:{uuid.uuid4().hex[:10]}"
    await graph.run(
        "ramp_create",
        {
            "handover": hid,
            "id": plan_id,
            "now": now_ms(),
            "method": method,
            "items": [
                {k: v for k, v in i.items() if k != "key"} | {"id": f"{plan_id}:{i['ord']}"}
                for i in items
            ],
        },
    )
    plan = await get(graph, hid)
    assert plan is not None
    return plan
