"""Who is calling, and what they may see or do.

Every access rule lives here, so the identity source can change without touching the rules:
today the caller comes from the demo "View as" header; later from a verified Keycloak login
(docs/identity-and-access.md). Rules combine a job-function role with relationships read from
the graph (docs/product-strategy.md section 10):

Roles (docs/identity-and-access.md section 0a):

- Platform admin (the Handovers team, `PLATFORM_ADMIN`): configures the organisation (integrations,
  sign-in, sample data). Not an employee: no home, people or handover content.
- HR runs handovers but never reads knowledge content or interview answers, and cannot approve.
- IT hands over a leaver's accounts. Exec sees the organisation overview, read-only.
- Managers (anyone with direct reports) run their team's handovers and approve transfers.
- One person approves each transfer: the leaver's manager; if there is none, or they are leaving
  too, the next manager up who is staying; if nobody is, HR (`pick_approver`).
- Who counts as HR, IT or leadership comes from the organisation's policy (services/org_policy.py):
  teams or departments, words in a job title, and sign-in groups.
- Only the leaver answers or confirms their exit-interview questions.
- People ask the companion as themselves, and change only their own privacy settings.

`None` as the caller means "unrestricted": no identity was supplied (tests, scripts, and the
app before a persona is chosen). The "View as" header is a demo stand-in and is not
authentication.
"""

from dataclasses import dataclass
from typing import Any

from core.graph import Graph
from services import org_policy

# The sample company's HR team (kept for seeds and tests; real roles come from the policy).
HR_TEAM = "team:people"
# The platform admin's caller id: an `Operator` node, not an `Employee`.
PLATFORM_ADMIN = "platform:admin"
# A transferred handover stays part of everyone's context: the successor ramps up on it, the
# leaver can still answer late questions, and the manager approves follow-ups. Only cancelled ends it.
ENDED = {"cancelled"}


@dataclass(frozen=True)
class Caller:
    id: str
    name: str
    title: str
    team: str | None
    roles: frozenset[str]
    reports: frozenset[str] = frozenset()
    # Chosen in "View as" (a demo guest), not signed in: may look, never change setup.
    guest: bool = False
    leaving: tuple[str, ...] = ()  # handovers (not cancelled) where the caller is the leaver
    succeeding: tuple[str, ...] = ()  # ... where the caller is the successor
    managing: tuple[str, ...] = ()  # ... of the caller's direct reports
    # Leavers whose transfer this caller approves (see pick_approver). None = not computed:
    # fall back to "the leaver's direct manager" (unit tests build callers by hand).
    approves: frozenset[str] | None = None

    @property
    def home(self) -> str:
        """Which home screen this person lands on (product-strategy section 10.2)."""
        if "platform_admin" in self.roles:
            return "platform"
        if self.leaving:
            return "leaver"
        if self.succeeding:
            return "successor"
        if "hr" in self.roles:
            return "overview"
        if "exec" in self.roles:
            # Leadership watches risk and outcomes; HR runs the handovers.
            return "leadership"
        if self.reports:
            return "manager"
        return "employee"


def _current(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    return tuple(r["id"] for r in rows if r.get("id") and r.get("status") not in ENDED)


def roles_for(team: str | None, title: str) -> frozenset[str]:
    """Roles under the default policy (the sample company). Live callers use the saved policy."""
    return org_policy.roles_for(org_policy.DEFAULTS, team, None, title)


def pick_approver(chain: list[dict[str, Any]]) -> dict[str, Any]:
    """Who approves a leaver's transfer, from their management chain (nearest first).

    The direct manager, unless they have left or are leaving too; then the next manager up who is
    staying; if nobody in the chain is, HR approves. Pure, so the rule is unit-tested.
    """
    for m in sorted((c for c in chain if c), key=lambda c: c.get("depth", 9)):
        if m.get("status") != "departed" and not m.get("leaving"):
            via = "manager" if m.get("depth") == 1 else "skip-level manager"
            return {"id": m["id"], "name": m.get("name"), "via": via}
    return {"id": None, "name": "HR", "via": "hr"}


async def approval_routes(graph: Graph) -> dict[str, dict[str, Any]]:
    """leaver id -> approver for every live handover."""
    return {r["leaver"]: pick_approver(r["chain"]) for r in await graph.read("approval_routes", {})}


async def hr_people(graph: Graph, policy: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Active HR people under the organisation's policy."""
    p = policy or await org_policy.load(graph)
    groups = [g.lower() for g, role in (p.get("role_groups") or {}).items() if role == "hr"]
    teams = sorted({t.strip().lower() for t in p["hr_teams"]})
    return await graph.read("hr_people", {"teams": teams, "groups": groups})


def platform_admin() -> Caller:
    """The Handovers team account: configures the organisation, sees no people or content."""
    return Caller(
        id=PLATFORM_ADMIN,
        name="Platform admin",
        title="Handovers team",
        team=None,
        roles=frozenset({"platform_admin"}),
    )


async def load_caller(graph: Graph, emp: str) -> Caller | None:
    if emp == PLATFORM_ADMIN:
        return platform_admin()
    row = await graph.one("access_caller", {"emp": emp})
    if row is None:
        return None
    reports = frozenset(r for r in row["reports"] or [] if r)
    policy = await org_policy.load(graph)
    roles = org_policy.roles_for(
        policy, row["team_id"], row["team"], row["title"] or "", row.get("groups") or []
    )
    if reports:
        roles |= {"manager"}
    routes = await approval_routes(graph)
    approves = frozenset(
        leaver
        for leaver, a in routes.items()
        if a["id"] == row["id"] or (a["via"] == "hr" and "hr" in roles and leaver != row["id"])
    )
    return Caller(
        id=row["id"],
        name=row["name"],
        title=row["title"] or "",
        team=row["team"],
        roles=roles,
        reports=reports,
        leaving=_current(row["leaving"] or []),
        succeeding=_current(row["succeeding"] or []),
        managing=_current(row["managing"] or []),
        approves=approves,
    )


# ------------------------------------------------------------------ rules (pure, unit-tested)


def is_manager_of(caller: Caller | None, employee_id: str) -> bool:
    return caller is not None and employee_id in caller.reports


def approves(caller: Caller | None, leaver_id: str) -> bool:
    """The caller is the one who approves this leaver's transfer."""
    if caller is None:
        return True
    if caller.approves is None:
        return is_manager_of(caller, leaver_id)
    return leaver_id in caller.approves


def can_view_handover(caller: Caller | None, leaver_id: str) -> bool:
    if caller is None:
        return True
    return (
        "hr" in caller.roles
        or is_manager_of(caller, leaver_id)
        or caller.id == leaver_id
        or approves(caller, leaver_id)
    )


def can_read_answers(caller: Caller | None, leaver_id: str) -> bool:
    """Interview answers and knowledge content: the leaver, their manager and the approver (a
    skip-level manager when the manager is away). Not HR, even when HR is the fallback approver."""
    if caller is None:
        return True
    if caller.id == leaver_id or is_manager_of(caller, leaver_id):
        return True
    return approves(caller, leaver_id) and "hr" not in caller.roles


def can_answer(caller: Caller | None, leaver_id: str) -> bool:
    return caller is None or caller.id == leaver_id


def can_run_handover(caller: Caller | None, leaver_id: str) -> bool:
    """Open, analyse, staff and hire for a handover: HR or the leaver's manager (not the leaver)."""
    if caller is None:
        return True
    return "hr" in caller.roles or is_manager_of(caller, leaver_id)


# What someone does and controls (work, accounts, contacts) is operational; HR needs the names.
OPERATIONAL = {"Account", "Responsibility", "Stakeholder"}


def redact_gaps(gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Progress without knowledge content: operational items keep their name, the rest the label."""
    keep = ("id", "rule", "label", "status", "priority", "interview", "target_kind")
    return [
        {k: g.get(k) for k in keep}
        | {
            "title": g.get("title") if g.get("target_kind") in OPERATIONAL else g.get("label"),
            "redacted": True,
        }
        for g in gaps
    ]


def can_approve(caller: Caller | None, leaver_id: str) -> bool:
    """Approve or reject the transfer and the ramp-up plan: the one approver (pick_approver)."""
    if caller is None:
        return True
    return caller.id != leaver_id and approves(caller, leaver_id)


def can_dismiss_question(caller: Caller | None, leaver_id: str, mandatory: bool) -> bool:
    """Drop an exit-interview question: never a mandatory one, and never the leaver (fewer
    questions would turn "answered" green sooner) or HR (who cannot read what it asks)."""
    if mandatory:
        return False
    if caller is None:
        return True
    return (
        caller.id != leaver_id
        and (is_manager_of(caller, leaver_id) or approves(caller, leaver_id))
        and can_read_answers(caller, leaver_id)
    )


def can_ask_question(caller: Caller | None, leaver_id: str) -> bool:
    """Add a question or a follow-up to a leaver's exit interview: HR or the manager."""
    return can_run_handover(caller, leaver_id) or (
        caller is not None and approves(caller, leaver_id) and caller.id != leaver_id
    )


def can_view_ramp(
    caller: Caller | None, leaver_id: str, successor_id: str | None, status: str | None
) -> bool:
    """HR and the manager see the plan; the successor sees it once the manager has approved it."""
    if caller is None:
        return True
    if "hr" in caller.roles or is_manager_of(caller, leaver_id):
        return True
    return caller.id == successor_id and status == "approved"


def can_tick_ramp(caller: Caller | None, successor_id: str | None) -> bool:
    return caller is None or caller.id == successor_id


def can_reassign_account(caller: Caller | None, leaver_id: str) -> bool:
    """Hand a leaver's account to someone else: IT, HR or the leaver's manager."""
    if caller is None:
        return True
    return "it" in caller.roles or can_run_handover(caller, leaver_id)


def can_assign_backup(caller: Caller | None, owners: list[str], backup: str) -> bool:
    """Add a backup owner: HR for anyone; a manager of a current owner, picking from their own team."""
    if caller is None or "hr" in caller.roles:
        return True
    manages_owner = any(is_manager_of(caller, o) for o in owners)
    return manages_owner and (backup in caller.reports or backup == caller.id)


def can_view_setup(caller: Caller | None) -> bool:
    """See integrations and sign-in: the platform admin, also as a "View as" guest (the demo)."""
    return caller is None or "platform_admin" in caller.roles


def can_configure(caller: Caller | None) -> bool:
    """Change integrations or sign-in, sync, reload the sample data: the signed-in platform admin.

    A guest viewing as the platform admin only looks, so a public demo keeps its seeded data.
    """
    return caller is None or ("platform_admin" in caller.roles and not caller.guest)


def can_act_as(caller: Caller | None, emp: str) -> bool:
    """Ask the companion as `emp`, or change `emp`'s privacy settings."""
    return caller is None or caller.id == emp


def can_view_person(caller: Caller | None, emp: str) -> bool:
    if caller is None:
        return True
    return caller.id == emp or is_manager_of(caller, emp) or "hr" in caller.roles


def can_view_org(caller: Caller | None) -> bool:
    """Organisation-wide dashboards and KPIs."""
    if caller is None:
        return True
    return bool(caller.roles & {"hr", "exec"})


def hide_private(person: dict[str, Any]) -> dict[str, Any]:
    """What anyone but the person sees: no items they kept private, nothing personal."""
    knowledge = [
        k
        for k in person.get("knowledge") or []
        if not k.get("private") and k.get("sensitivity") != "personal"
    ]
    recent = [s for s in person.get("recent") or [] if s.get("sensitivity") != "personal"]
    return {**person, "knowledge": knowledge, "recent": recent}


def redact_excluded(preview: dict[str, Any]) -> dict[str, Any]:
    """The manager sees that private or personal items stay behind, never what they are."""
    exclude = [
        {**x, "id": f"private:{i}", "title": "Private item"}
        if x.get("reason") in {"personal", "private"}
        else x
        for i, x in enumerate(preview.get("exclude") or [])
    ]
    return {**preview, "exclude": exclude}


def redact_person(person: dict[str, Any]) -> dict[str, Any]:
    """HR sees what someone does and controls, but not the content of what they know."""
    knowledge = person.get("knowledge") or []
    return {**person, "knowledge": [], "knowledge_count": len(knowledge), "redacted": True}


def describe(caller: Caller) -> dict[str, Any]:
    return {
        "id": caller.id,
        "name": caller.name,
        "title": caller.title,
        "team": caller.team,
        "roles": sorted(caller.roles),
        "home": caller.home,
        "reports": sorted(caller.reports),
        "leaving": list(caller.leaving),
        "succeeding": list(caller.succeeding),
        "managing": list(caller.managing),
        "guest": caller.guest,
    }


async def personas(graph: Graph) -> list[dict[str, Any]]:
    """Demo identities for "View as": one person per role in the open handovers, plus HR,
    leadership and an ordinary employee."""
    handovers = await graph.read("handover_list")
    people = await graph.read("people_directory")
    picked: list[tuple[str, str]] = []

    def add(emp: str | None, label: str) -> None:
        if emp and emp not in {p for p, _ in picked}:
            picked.append((emp, label))

    for p in people:
        caller = await load_caller(graph, p["id"])
        if caller and "exec" in caller.roles:
            add(caller.id, "Leadership")
        if caller and "hr" in caller.roles:
            add(caller.id, "HR & Admin")
    for h in handovers:
        if h["status"] in ENDED:
            continue
        detail = await graph.one("handover_get", {"id": h["id"]})
        if detail is None:
            continue
        add(detail["employee_id"], "Leaving")
        add(detail.get("manager_id"), "Manager")
        add(detail.get("successor_id"), "Successor")
    involved = {p for p, _ in picked}
    for p in people:
        if p["id"] not in involved and p.get("status") == "active":
            add(p["id"], "Employee")
            break

    by_id = {p["id"]: p for p in people}
    admin = platform_admin()
    return [
        {"id": admin.id, "name": admin.name, "title": admin.title, "label": "Platform admin"}
    ] + [
        {"id": emp, "name": by_id[emp]["name"], "title": by_id[emp]["title"], "label": label}
        for emp, label in picked
        if emp in by_id
    ]
