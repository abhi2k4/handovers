"""Generate the synthetic company "Northwind" as connector-shaped fixtures.

Deterministic (fixed RNG seed). Everything is fictional. Output: graph/seed/northwind/
  org.json            teams, roles, employees, areas, skill catalog (with resume aliases)
  sources.jsonl       one SourceIn per line: EOD reports, tickets, PRs, messages, meetings, docs,
                      each carrying the facts an extractor would produce from it
  interview.json      scripted exit-interview answers for the demo, keyed by gap target
  benchmark.json      successor questions with gold knowledge ids, plus abstention traps

Two leavers carry parallel storylines:
  Arjun Mehta  (Senior Backend Engineer)       Nisha Verma (Performance Marketing Manager)
  - undocumented change: retry limit 5 -> 3      - Google Ads paused, no reason recorded
  - recurring fix, no procedure: ledger batches  - month-end UTM sheet rebuild, no procedure
  - sole access: prod DB migrator, bank portal   - sole admin: Meta Business Manager, GA4
  - sole relationship: AcmeBank TAM              - sole relationships: agency lead, Mixpanel CSM
  - contradiction: runbook says 5, code says 3   - contradiction: deck says CAC 600, EODs say 450
  - private: 1:1 career notes                    - private: salary notes
  - control (shared, not at risk): settlement v2 - control: Reels budget decision, A/B tests

Run:  uv run python -m seed.generate
"""

import json
import random
from datetime import date, datetime, timedelta
from typing import Any

from core.config import get_settings

RNG = random.Random(42)
IST = "+05:30"

# ------------------------------------------------------------------------------------- org

TEAMS = [
    {"id": "team:leadership", "name": "Leadership"},
    {"id": "team:people", "name": "People"},
    {"id": "team:engineering", "name": "Engineering"},
    {"id": "team:growth", "name": "Growth"},
    {"id": "team:sales", "name": "Sales & Success"},
    {"id": "team:finance", "name": "Finance"},
]

ROLES = [
    {"id": "role:ceo", "title": "Chief Executive Officer"},
    {"id": "role:hr", "title": "HR & Admin Lead"},
    {"id": "role:em", "title": "Engineering Manager"},
    {"id": "role:backend", "title": "Backend Engineer"},
    {"id": "role:frontend", "title": "Frontend Engineer"},
    {"id": "role:platform", "title": "Platform Engineer"},
    {"id": "role:growth-lead", "title": "Head of Growth"},
    {"id": "role:performance", "title": "Performance Marketer"},
    {"id": "role:content", "title": "Content Marketer"},
    {"id": "role:designer", "title": "Product Designer"},
    {"id": "role:sales-lead", "title": "Head of Sales"},
    {"id": "role:ae", "title": "Account Executive"},
    {"id": "role:csm", "title": "Customer Success Manager"},
    {"id": "role:finance", "title": "Finance Manager"},
]


def emp(
    key: str,
    name: str,
    title: str,
    team: str,
    role: str,
    manager: str | None,
    joined: str,
    status: str = "active",
) -> dict[str, Any]:
    first = name.split()[0].lower()
    return {
        "id": f"emp:{key}",
        "name": name,
        "email": f"{first}@northwind.example",
        "title": title,
        "team": f"team:{team}",
        "role": f"role:{role}",
        "manager": f"emp:{manager}" if manager else None,
        "status": status,
        "joined_at": joined,
    }


EMPLOYEES = [
    emp("kavya", "Kavya Rao", "Founder & CEO", "leadership", "ceo", None, "2021-04-01"),
    emp("meera", "Meera Iyer", "HR & Admin Lead", "people", "hr", "kavya", "2022-01-10"),
    emp("priya", "Priya Nair", "Engineering Manager", "engineering", "em", "kavya", "2021-09-01"),
    emp(
        "arjun",
        "Arjun Mehta",
        "Senior Backend Engineer",
        "engineering",
        "backend",
        "priya",
        "2022-08-01",
    ),
    emp("rohan", "Rohan Das", "Backend Engineer", "engineering", "backend", "priya", "2023-05-15"),
    emp("sana", "Sana Khan", "Frontend Engineer", "engineering", "frontend", "priya", "2023-01-09"),
    emp(
        "vikram",
        "Vikram Shah",
        "Platform Engineer",
        "engineering",
        "platform",
        "priya",
        "2022-11-21",
    ),
    emp(
        "farhan",
        "Farhan Sheikh",
        "Backend Engineer",
        "engineering",
        "backend",
        "priya",
        "2026-10-19",
        "incoming",
    ),
    emp("aditi", "Aditi Menon", "Head of Growth", "growth", "growth-lead", "kavya", "2021-11-01"),
    emp(
        "nisha",
        "Nisha Verma",
        "Performance Marketing Manager",
        "growth",
        "performance",
        "aditi",
        "2023-02-13",
    ),
    emp("kabir", "Kabir Malhotra", "Content Marketer", "growth", "content", "aditi", "2024-03-04"),
    emp("tara", "Tara Joseph", "Product Designer", "growth", "designer", "aditi", "2023-07-17"),
    emp(
        "ananya",
        "Ananya Pillai",
        "Performance Marketer",
        "growth",
        "performance",
        "aditi",
        "2026-10-26",
        "incoming",
    ),
    emp("dev", "Dev Kapoor", "Head of Sales", "sales", "sales-lead", "kavya", "2022-03-14"),
    emp("ishaan", "Ishaan Gupta", "Account Executive", "sales", "ae", "dev", "2024-01-22"),
    emp("zoya", "Zoya Ali", "Customer Success Manager", "sales", "csm", "dev", "2023-09-04"),
    emp("rahul", "Rahul Bose", "Finance Manager", "finance", "finance", "kavya", "2022-06-06"),
]

AREAS = [
    ("area:recon-service", "Reconciliation service", "service"),
    ("area:ledger-export", "Ledger export", "service"),
    ("area:platform-db", "Production database", "infrastructure"),
    ("area:bank-integration", "AcmeBank integration", "integration"),
    ("area:backend", "Backend codebase", "codebase"),
    ("area:settlement-v2", "Settlement v2", "project"),
    ("area:frontend", "Web app", "codebase"),
    ("area:infra", "Cloud infrastructure", "infrastructure"),
    ("area:paid-social", "Paid social", "channel"),
    ("area:paid-search", "Paid search", "channel"),
    ("area:attribution", "Attribution", "process"),
    ("area:growth-reporting", "Growth reporting", "process"),
    ("area:creative", "Ad creatives", "process"),
    ("area:landing-pages", "Landing pages", "channel"),
    ("area:content", "Content", "channel"),
    ("area:sales-pipeline", "Sales pipeline", "process"),
    ("area:customer-success", "Customer accounts", "process"),
    ("area:finance-ops", "Finance operations", "process"),
]

SKILLS: list[tuple[str, str, str, list[str]]] = [
    ("skill:python", "Python", "skill", ["python", "python3"]),
    ("skill:fastapi", "FastAPI", "tool", ["fastapi"]),
    ("skill:postgresql", "PostgreSQL", "tool", ["postgresql", "postgres", "psql"]),
    (
        "skill:alembic",
        "Database migrations",
        "skill",
        ["alembic", "database migrations", "schema migrations", "flyway", "liquibase"],
    ),
    (
        "skill:rest-apis",
        "REST API integrations",
        "skill",
        [
            "rest api",
            "rest apis",
            "api integration",
            "api integrations",
            "webhooks",
            "third-party apis",
        ],
    ),
    (
        "skill:payments",
        "Payments & reconciliation",
        "domain",
        ["payments", "reconciliation", "settlement", "ledger", "fintech"],
    ),
    (
        "skill:observability",
        "Monitoring & on-call",
        "skill",
        ["sentry", "grafana", "datadog", "monitoring", "on-call", "incident response"],
    ),
    (
        "skill:security",
        "Secrets & key management",
        "skill",
        ["key rotation", "secrets management", "vault", "api keys"],
    ),
    (
        "skill:code-review",
        "Code review",
        "skill",
        ["code review", "code reviews", "pull request reviews"],
    ),
    ("skill:docker", "Docker", "tool", ["docker", "containers", "kubernetes"]),
    ("skill:gcp", "Google Cloud", "tool", ["gcp", "google cloud", "cloud sql", "cloud run"]),
    ("skill:react", "React", "tool", ["react", "react.js", "reactjs"]),
    ("skill:typescript", "TypeScript", "skill", ["typescript"]),
    (
        "skill:meta-ads",
        "Meta Ads Manager",
        "tool",
        ["meta ads", "facebook ads", "instagram ads", "ads manager", "meta business manager"],
    ),
    ("skill:google-ads", "Google Ads", "tool", ["google ads", "adwords", "sem", "search ads"]),
    ("skill:ga4", "Google Analytics 4", "tool", ["ga4", "google analytics"]),
    ("skill:utm", "UTM & attribution", "skill", ["utm", "attribution", "multi-touch attribution"]),
    ("skill:looker-studio", "Looker Studio", "tool", ["looker studio", "data studio"]),
    (
        "skill:sheets",
        "Spreadsheets",
        "tool",
        ["google sheets", "excel", "spreadsheets", "spreadsheet"],
    ),
    (
        "skill:cac-roas",
        "CAC & ROAS optimisation",
        "domain",
        ["cac", "roas", "cpa", "cost per acquisition", "return on ad spend"],
    ),
    (
        "skill:ab-testing",
        "A/B testing",
        "skill",
        ["a/b test", "a/b testing", "ab testing", "experiments"],
    ),
    (
        "skill:creative-briefing",
        "Creative briefing",
        "skill",
        ["creative brief", "creative briefs", "agency management", "briefing agencies"],
    ),
    (
        "skill:copywriting",
        "Copywriting",
        "skill",
        ["copywriting", "content writing", "blog writing"],
    ),
    (
        "skill:seo",
        "SEO",
        "skill",
        ["seo", "search engine optimisation", "search engine optimization"],
    ),
    ("skill:figma", "Figma", "tool", ["figma"]),
    ("skill:mixpanel", "Mixpanel", "tool", ["mixpanel", "product analytics"]),
    ("skill:hubspot", "HubSpot CRM", "tool", ["hubspot", "crm"]),
    ("skill:negotiation", "Negotiation", "skill", ["negotiation", "closing deals"]),
    ("skill:fpna", "FP&A", "domain", ["fp&a", "financial planning", "budgeting", "forecasting"]),
]

# ------------------------------------------------------------------------------------- helpers

SOURCES: list[dict[str, Any]] = []


def ts(day: date | str, hour: int = 18, minute: int = 30) -> str:
    d = date.fromisoformat(day) if isinstance(day, str) else day
    return datetime(d.year, d.month, d.day, hour, minute).isoformat() + IST


def fact(kind: str, key: str, title: str, **kw: Any) -> dict[str, Any]:
    return {
        "kind": kind,
        "key": key,
        "title": title,
        **{k: v for k, v in kw.items() if v is not None},
    }


def resp(
    key: str, title: str, cadence: str, area: str, skills: list[str], **kw: Any
) -> dict[str, Any]:
    return fact("responsibility", key, title, cadence=cadence, area=area, skills=skills, **kw)


def add(
    sid: str,
    kind: str,
    system: str,
    title: str,
    text: str,
    at: str,
    author: str | None,
    facts: list[dict[str, Any]] | None = None,
    **kw: Any,
) -> None:
    src = {
        "id": sid,
        "kind": kind,
        "system": system,
        "title": title,
        "text": text,
        "occurred_at": at,
        "author": author,
        "facts": facts or [],
    }
    src.update({k: v for k, v in kw.items() if v is not None})
    SOURCES.append(src)


def weekdays(start: str, end: str) -> list[date]:
    d, stop, out = date.fromisoformat(start), date.fromisoformat(end), []
    while d <= stop:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


EOD_START, EOD_END = "2026-04-06", "2026-10-09"

# ------------------------------------------------------------------------------------- Arjun

R_RECON = resp(
    "resp:recon-service",
    "Own the reconciliation service: deploys, alerts and fixes",
    "daily",
    "area:recon-service",
    ["skill:python", "skill:postgresql", "skill:observability", "skill:payments"],
)
R_LEDGER = resp(
    "resp:ledger-unstick",
    "Unstick hung ledger-export batches",
    "monthly",
    "area:ledger-export",
    ["skill:postgresql", "skill:python"],
)
R_MIGRATIONS = resp(
    "resp:prod-migrations",
    "Run production database migrations",
    "weekly",
    "area:platform-db",
    ["skill:alembic", "skill:postgresql"],
)
R_ACME = resp(
    "resp:acmebank-integration",
    "Maintain the AcmeBank settlement API integration",
    "weekly",
    "area:bank-integration",
    ["skill:rest-apis", "skill:python", "skill:payments"],
)
R_KEYS = resp(
    "resp:acmebank-key-rotation",
    "Rotate AcmeBank API keys",
    "quarterly",
    "area:bank-integration",
    ["skill:security"],
)
R_REVIEW = resp(
    "resp:backend-review",
    "Review backend pull requests",
    "daily",
    "area:backend",
    ["skill:code-review", "skill:python"],
)
R_SETTLE = resp(
    "resp:settlement-v2",
    "Deliver the Settlement v2 migration",
    "weekly",
    "area:settlement-v2",
    ["skill:python", "skill:postgresql", "skill:payments"],
)

A_MIGRATOR = fact(
    "access",
    "acc:prod-db-migrator",
    "Production database (migration role)",
    system="Cloud SQL",
    role="admin",
    area="area:platform-db",
)
A_ACME_PORTAL = fact(
    "access",
    "acc:acmebank-portal",
    "AcmeBank developer portal",
    system="AcmeBank",
    role="admin",
    area="area:bank-integration",
)
A_VERCEL = fact(
    "access", "acc:vercel", "Vercel team", system="Vercel", role="admin", area="area:frontend"
)
S_ACME_TAM = fact(
    "stakeholder",
    "sth:acmebank-leena",
    "Leena Kurian",
    org="AcmeBank",
    stakeholder_kind="partner",
    context="Technical account manager for the settlement API",
    area="area:bank-integration",
)


def arjun_history() -> None:
    a = "emp:arjun"
    add(
        "src:doc:adr-007",
        "Document",
        "docs",
        "ADR-007: Retry policy for bank settlement calls",
        "Context: AcmeBank's settlement API returns intermittent 502s during their batch window.\n"
        "Decision: retry settlement calls up to 5 times with exponential backoff (1, 2, 4, 8, 16 minutes).\n"
        "Consequences: covers ~99% of transient failures seen in February.",
        ts("2024-03-01", 11),
        a,
        doc_type="adr",
        attendees=["emp:priya"],
        areas=["area:recon-service"],
        skills=["skill:payments", "skill:rest-apis"],
        facts=[
            fact(
                "decision",
                "dec:recon-retry-5",
                "Retry AcmeBank settlement calls up to 5 times",
                rationale="Bank API returns intermittent 502s in its batch window; 5 retries with exponential backoff covered ~99% of transient failures.",
                alternatives=["Fail fast and alert", "Fixed 3 retries"],
                area="area:recon-service",
                people=[a, "emp:priya"],
                quote="retry settlement calls up to 5 times with exponential backoff",
            ),
            fact(
                "claim",
                "clm:recon-retry-limit@2024",
                "Reconciliation service retries settlement calls 5 times",
                subject="svc:recon",
                predicate="retry_limit",
                value="5",
                justified_by="dec:recon-retry-5",
                area="area:recon-service",
                people=[a, "emp:priya"],
            ),
        ],
    )
    add(
        "src:doc:recon-runbook",
        "Document",
        "docs",
        "Recon service runbook",
        "Deploy: merge to main, wait for CI, run `make deploy-recon`, watch the Sentry release dashboard for 15 minutes.\n"
        "Retries: settlement calls retry 5 times before paging.\nPager: #recon-alerts.",
        ts("2024-03-05", 12),
        a,
        doc_type="runbook",
        areas=["area:recon-service"],
        skills=["skill:observability"],
        facts=[
            fact(
                "procedure",
                "proc:deploy-recon",
                "Deploy the reconciliation service",
                steps=[
                    "Merge to main and wait for CI",
                    "Run make deploy-recon",
                    "Watch the Sentry release dashboard for 15 minutes",
                ],
                handles="resp:recon-service",
                area="area:recon-service",
                people=[a, "emp:rohan"],
            ),
            fact(
                "claim",
                "clm:recon-retry-limit@runbook",
                "Runbook: settlement calls retry 5 times before paging",
                subject="svc:recon",
                predicate="retry_limit",
                value="5",
                area="area:recon-service",
                people=[a, "emp:rohan"],
            ),
        ],
    )
    add(
        "src:ticket:inc-2291",
        "Ticket",
        "jira",
        "INC-2291: Duplicate settlement payouts",
        "Sev-1. 14 merchants received duplicate payouts on 3 June. Root cause under investigation; recon retries suspected.",
        ts("2025-06-03", 15),
        a,
        status="closed",
        areas=["area:recon-service"],
        skills=["skill:observability", "skill:payments"],
        facts=[R_RECON],
    )
    add(
        "src:meeting:retro-2291",
        "Meeting",
        "calendar",
        "Retro: INC-2291 duplicate payouts",
        "Retries 4 and 5 fired after AcmeBank's 15-minute idempotency window, so the bank treated them as new payouts. "
        "Action: cap retries so total backoff stays under 15 minutes. Owner: Arjun.",
        ts("2025-06-04", 16),
        a,
        attendees=["emp:priya", "emp:rahul"],
        areas=["area:recon-service"],
    )
    add(
        "src:pr:418",
        "PullRequest",
        "github",
        "#418 recon: lower retry limit to 3",
        "Lower settlement retry limit from 5 to 3.",
        ts("2025-06-12", 13),
        a,
        url="https://github.example/northwind/payments/pull/418",
        areas=["area:recon-service"],
        skills=["skill:python"],
        facts=[
            fact(
                "claim",
                "clm:recon-retry-limit@2025",
                "Reconciliation service retries settlement calls 3 times",
                subject="svc:recon",
                predicate="retry_limit",
                value="3",
                supersedes="clm:recon-retry-limit@2024",
                area="area:recon-service",
                quote="Lower settlement retry limit from 5 to 3.",
            ),
            R_RECON,
        ],
    )
    add(
        "src:doc:settle-v2",
        "Document",
        "docs",
        "Settlement v2 design",
        "Batch settlements every 30 minutes instead of calling the bank per transaction. Cuts API calls by ~90% and "
        "keeps us inside AcmeBank's rate limits. Rollout behind a per-merchant flag.",
        ts("2026-03-10", 11),
        "emp:rohan",
        doc_type="design",
        attendees=[a, "emp:priya"],
        areas=["area:settlement-v2"],
        skills=["skill:payments", "skill:postgresql"],
        facts=[
            fact(
                "decision",
                "dec:settle-v2-batching",
                "Batch settlements every 30 minutes",
                rationale="Cuts bank API calls by ~90% and keeps us inside AcmeBank rate limits.",
                alternatives=["Per-transaction calls", "Hourly batches"],
                area="area:settlement-v2",
                people=["emp:rohan", a, "emp:priya"],
            ),
            dict(R_SETTLE, people=["emp:rohan", a]),
        ],
    )
    add(
        "src:doc:arjun-1on1",
        "Document",
        "docs",
        "1:1 notes — Arjun / Priya",
        "Career: Arjun is weighing an offer from a Bengaluru fintech; wants a staff-level path. Follow up next month.",
        ts("2026-08-14", 17),
        a,
        doc_type="notes",
        attendees=["emp:priya"],
        sensitivity="personal",
        facts=[
            fact(
                "claim",
                "clm:arjun-career",
                "Arjun is weighing an external offer",
                subject="emp:arjun",
                predicate="career_note",
                value="weighing offer",
                people=[a, "emp:priya"],
            )
        ],
    )
    # Sole access and relationship evidence.
    add(
        "src:msg:acme-portal-admin",
        "Message",
        "slack",
        "#payments-eng",
        "Reminder: I'm the only admin on the AcmeBank developer portal and the prod DB migration role. "
        "Will add a second admin when Settlement v2 ships.",
        ts("2026-05-20", 11),
        a,
        areas=["area:bank-integration"],
        facts=[
            dict(A_ACME_PORTAL, quote="I'm the only admin on the AcmeBank developer portal"),
            dict(A_MIGRATOR, quote="the prod DB migration role"),
        ],
    )
    add(
        "src:msg:vercel-admins",
        "Message",
        "slack",
        "#frontend",
        "Added Arjun as a second Vercel admin so deploys don't block on me. — Sana",
        ts("2026-04-15", 10),
        "emp:sana",
        areas=["area:frontend"],
        facts=[dict(A_VERCEL, people=["emp:sana", a])],
    )


ARJUN_EOD = {
    "recon": (
        R_RECON,
        [
            "Deployed recon-service {v}; watched Sentry for 15 min, clean.",
            "Fixed recon mismatch for {m} merchants caused by a late bank file; reran the job.",
            "Triaged {n} recon alerts; one real issue (timezone on the cut-off), patched.",
            "Recon: added a guard for partial bank files. Deployed {v}.",
        ],
        ["skill:python", "skill:observability", "skill:payments"],
    ),
    "migrations": (
        R_MIGRATIONS,
        [
            "Ran prod migration {mig} (alembic) during the low-traffic window. No locks.",
            "Prepared migration {mig}; dry-run on staging clone took 40s.",
            "Ran prod migration {mig}; had to split an index build to avoid table locks.",
        ],
        ["skill:alembic", "skill:postgresql"],
    ),
    "acme": (
        R_ACME,
        [
            "AcmeBank: synced with Leena on the new settlement file format, starts next month.",
            "Handled AcmeBank 502 burst during their batch window; retries absorbed it.",
            "Updated the AcmeBank client for the v3 status codes.",
        ],
        ["skill:rest-apis", "skill:payments"],
    ),
    "review": (
        R_REVIEW,
        [
            "Reviewed {n} backend PRs.",
            "Code review for Rohan's settlement batching PR.",
            "Reviewed {n} PRs, left notes on query plans.",
        ],
        ["skill:code-review", "skill:python"],
    ),
    "settle": (
        R_SETTLE,
        [
            "Settlement v2: wired the per-merchant flag.",
            "Settlement v2: load test with 30-minute batches, fine at 4x volume.",
        ],
        ["skill:python", "skill:postgresql"],
    ),
}


def arjun_eods() -> None:
    a = "emp:arjun"
    version = 140
    mig = 212
    for d in weekdays(EOD_START, EOD_END):
        if RNG.random() > 0.62:
            continue
        picks = RNG.sample(list(ARJUN_EOD), k=RNG.choice([1, 2, 2, 3]))
        if "recon" not in picks and RNG.random() < 0.6:
            picks[0] = "recon"
        lines, facts, skills = [], [], set()
        for p in dict.fromkeys(picks):
            r, templates, sk = ARJUN_EOD[p]
            version += 1 if p == "recon" else 0
            mig += 1 if p == "migrations" else 0
            lines.append(
                RNG.choice(templates).format(
                    v=f"v2.{version}", m=RNG.randint(2, 30), n=RNG.randint(2, 7), mig=f"0{mig}"
                )
            )
            facts.append(r)
            skills.update(sk)
            if p == "acme" and "Leena" in lines[-1]:
                facts.append(dict(S_ACME_TAM, quote="synced with Leena"))
            if p == "migrations":
                facts.append(A_MIGRATOR)
        add(
            f"src:eod:arjun:{d}",
            "EOD",
            "eod",
            f"EOD {d:%d %b}",
            "\n".join(f"- {line}" for line in lines),
            ts(d),
            a,
            skills=sorted(skills),
            areas=sorted({f["area"] for f in facts if "area" in f}),
            facts=facts,
        )
    for ds in ("2026-04-07", "2026-07-06"):
        add(
            f"src:eod:arjun:{ds}:keys",
            "EOD",
            "eod",
            f"EOD {date.fromisoformat(ds):%d %b} (keys)",
            "- Rotated the AcmeBank API keys (quarterly). New key in Secret Manager; old key revoked after 24h.",
            ts(ds, 19),
            a,
            skills=["skill:security"],
            areas=["area:bank-integration"],
            facts=[R_KEYS, A_ACME_PORTAL],
        )
    # Recurring manual fix: ledger batches (tickets + the fix described only in Slack).
    for i, ds in enumerate(["2026-04-21", "2026-06-02", "2026-07-14", "2026-08-25", "2026-09-29"]):
        last = i == 4
        add(
            f"src:ticket:ledger-{301 + i}",
            "Ticket",
            "jira",
            f"LEDGER-{301 + i}: Ledger export batch stuck",
            "Nightly ledger export stuck in RUNNING since 02:10. Finance waiting on the file.",
            ts(ds, 9),
            a,
            status="open" if last else "closed",
            areas=["area:ledger-export"],
            skills=["skill:postgresql"],
            facts=[R_LEDGER],
        )
        if not last:
            add(
                f"src:msg:ledger-fix-{i}",
                "Message",
                "slack",
                "#payments-eng",
                "Ledger export unstuck: cleared the advisory lock row in export_locks, re-queued with --skip-locked. "
                "Finance has the file.",
                ts(ds, 11),
                a,
                areas=["area:ledger-export"],
                skills=["skill:postgresql"],
                facts=[R_LEDGER],
            )


# ------------------------------------------------------------------------------------- Nisha

R_META = resp(
    "resp:meta-ads",
    "Run Meta Ads campaigns and the weekly performance review",
    "weekly",
    "area:paid-social",
    ["skill:meta-ads", "skill:cac-roas"],
)
R_PACING = resp(
    "resp:budget-pacing",
    "Track daily budget pacing and CAC",
    "daily",
    "area:paid-social",
    ["skill:cac-roas", "skill:sheets"],
)
R_UTM = resp(
    "resp:utm-rebuild",
    "Rebuild the UTM attribution sheet at month-end",
    "monthly",
    "area:attribution",
    ["skill:utm", "skill:sheets", "skill:ga4"],
)
R_CEO_REPORT = resp(
    "resp:growth-report",
    "Send the monthly growth report to the CEO",
    "monthly",
    "area:growth-reporting",
    ["skill:ga4", "skill:looker-studio"],
)
R_AGENCY = resp(
    "resp:agency-briefs",
    "Brief and review creatives with Pixel & Pine",
    "weekly",
    "area:creative",
    ["skill:creative-briefing"],
)
R_LP = resp(
    "resp:lp-tests",
    "Run landing page A/B tests",
    "biweekly",
    "area:landing-pages",
    ["skill:ab-testing"],
)

A_META_BM = fact(
    "access",
    "acc:meta-business-manager",
    "Meta Business Manager",
    system="Meta",
    role="admin",
    area="area:paid-social",
)
A_GA4 = fact(
    "access",
    "acc:ga4",
    "Google Analytics 4 property",
    system="Google",
    role="admin",
    area="area:attribution",
)
A_GADS = fact(
    "access",
    "acc:google-ads",
    "Google Ads account",
    system="Google",
    role="admin",
    area="area:paid-search",
)
A_MIXPANEL = fact(
    "access",
    "acc:mixpanel",
    "Mixpanel workspace",
    system="Mixpanel",
    role="admin",
    area="area:growth-reporting",
)
S_AGENCY = fact(
    "stakeholder",
    "sth:pixelpine-rhea",
    "Rhea Sethi",
    org="Pixel & Pine",
    stakeholder_kind="agency",
    context="Agency lead for paid social creatives",
    area="area:creative",
)
S_MIXPANEL = fact(
    "stakeholder",
    "sth:mixpanel-tom",
    "Tom Becker",
    org="Mixpanel",
    stakeholder_kind="vendor",
    context="Customer success manager; annual contract renews 15 Nov",
    area="area:growth-reporting",
)


def nisha_history() -> None:
    n = "emp:nisha"
    add(
        "src:doc:q2-growth-deck",
        "Document",
        "docs",
        "Q2 growth plan (deck)",
        "Targets: blended CAC ₹600. Shift 30% of paid social budget to Reels (Reels CPM was 40% lower in March tests). "
        "Keep Google Ads at current spend.",
        ts("2026-04-02", 15),
        n,
        doc_type="deck",
        attendees=["emp:aditi", "emp:kavya"],
        areas=["area:paid-social"],
        skills=["skill:meta-ads", "skill:cac-roas"],
        facts=[
            fact(
                "claim",
                "clm:cac-target@q2",
                "Blended CAC target is ₹600",
                subject="growth:paid",
                predicate="cac_target",
                value="₹600",
                area="area:paid-social",
                people=[n, "emp:aditi", "emp:kavya"],
            ),
            fact(
                "decision",
                "dec:reels-30",
                "Shift 30% of paid social budget to Reels",
                rationale="Reels CPM was 40% lower than feed placements in March tests.",
                alternatives=["Keep feed-only", "Shift 50%"],
                area="area:paid-social",
                people=[n, "emp:aditi"],
            ),
        ],
    )
    add(
        "src:msg:google-ads-paused",
        "Message",
        "slack",
        "#growth",
        "Paused all Google Ads campaigns as of today. Budget moves to Meta from next week.",
        ts("2026-06-19", 18),
        n,
        areas=["area:paid-search"],
        skills=["skill:google-ads"],
        facts=[
            fact(
                "decision",
                "dec:pause-google-ads",
                "Pause all Google Ads campaigns",
                area="area:paid-search",
                quote="Paused all Google Ads campaigns as of today.",
            )
        ],
    )
    add(
        "src:msg:ga4-admins",
        "Message",
        "slack",
        "#growth",
        "FYI I'm still the only admin on Meta Business Manager and GA4. Kabir has viewer access on GA4.",
        ts("2026-05-11", 12),
        n,
        areas=["area:paid-social", "area:attribution"],
        facts=[
            dict(A_META_BM, quote="the only admin on Meta Business Manager"),
            dict(A_GA4, quote="and GA4"),
        ],
    )
    add(
        "src:msg:gads-admins",
        "Message",
        "slack",
        "#growth",
        "Aditi and I are both admins on the Google Ads account.",
        ts("2026-04-09", 12),
        n,
        areas=["area:paid-search"],
        facts=[dict(A_GADS, people=[n, "emp:aditi"])],
    )
    add(
        "src:crm:mixpanel-renewal",
        "CRMNote",
        "hubspot",
        "Mixpanel renewal call",
        "Call with Tom Becker (Mixpanel CSM): annual contract renews 15 Nov; asked for seat-based pricing. Nisha is the admin.",
        ts("2026-09-08", 16),
        n,
        areas=["area:growth-reporting"],
        skills=["skill:mixpanel"],
        facts=[
            S_MIXPANEL,
            A_MIXPANEL,
            fact(
                "claim",
                "clm:mixpanel-renewal",
                "Mixpanel contract renews on 15 Nov",
                subject="vendor:mixpanel",
                predicate="renewal_date",
                value="2026-11-15",
                area="area:growth-reporting",
            ),
        ],
    )
    add(
        "src:doc:nisha-salary-notes",
        "Document",
        "docs",
        "Notes for my salary discussion",
        "Ask for 18%. Market data from two recruiter calls.",
        ts("2026-07-22", 21),
        n,
        doc_type="notes",
        sensitivity="personal",
        facts=[
            fact(
                "claim",
                "clm:nisha-salary",
                "Salary discussion notes",
                subject="emp:nisha",
                predicate="salary_note",
                value="private",
            )
        ],
    )
    for i, d in enumerate(
        ["2026-04-30", "2026-05-29", "2026-06-30", "2026-07-31", "2026-08-31", "2026-09-30"]
    ):
        add(
            f"src:ticket:utm-{i}",
            "Ticket",
            "asana",
            "Month-end: rebuild UTM attribution sheet",
            "Rebuild the attribution sheet before the CEO report. Source: GA4 export + Meta UTMs.",
            ts(d, 10),
            n,
            status="closed",
            areas=["area:attribution"],
            skills=["skill:utm", "skill:sheets"],
            facts=[R_UTM],
        )
    for d in ("2026-04-08", "2026-06-24", "2026-09-02"):
        add(
            f"src:eod:tara:{d}:lp",
            "EOD",
            "eod",
            f"EOD {date.fromisoformat(d):%d %b}",
            "- Shipped the new landing page variant with Nisha; test runs two weeks.",
            ts(d),
            "emp:tara",
            skills=["skill:ab-testing", "skill:figma"],
            areas=["area:landing-pages"],
            facts=[dict(R_LP, people=["emp:tara", n])],
        )


NISHA_EOD = {
    "meta": (
        R_META,
        [
            "Meta: paused 3 fatigued ad sets, scaled the Reels winner by 20%.",
            "Weekly Meta review: CTR {ctr}%, frequency 2.1, launching new hooks Thursday.",
            "Rebuilt Meta audiences after the pixel update; lookalikes refreshed.",
            "Meta: CPM up {cpm}% this week, shifted budget toward Reels.",
        ],
        ["skill:meta-ads", "skill:cac-roas"],
    ),
    "pacing": (
        R_PACING,
        [
            "Pacing at {p}% of monthly budget. CAC ₹{cac} vs ₹450 target.",
            "CAC ₹{cac} against the ₹450 target; trimmed broad audiences.",
            "Budget pacing check: on track ({p}%).",
        ],
        ["skill:cac-roas", "skill:sheets"],
    ),
    "report": (
        R_CEO_REPORT,
        [
            "Pulled GA4 + Mixpanel numbers for the monthly growth report.",
            "Looker Studio dashboard fixed (GA4 connector re-auth).",
        ],
        ["skill:ga4", "skill:looker-studio"],
    ),
    "agency": (
        R_AGENCY,
        [
            "Briefed Pixel & Pine on next week's creatives (3 hooks, 2 formats).",
            "Reviewed agency creatives with Rhea; sent back 2 for edits.",
        ],
        ["skill:creative-briefing"],
    ),
    "utm": (
        R_UTM,
        ["Fixed broken UTMs on two campaigns; GA4 attribution looks sane again."],
        ["skill:utm", "skill:ga4"],
    ),
}


def nisha_eods() -> None:
    n = "emp:nisha"
    for d in weekdays(EOD_START, EOD_END):
        if RNG.random() > 0.62:
            continue
        picks = RNG.sample(list(NISHA_EOD), k=RNG.choice([1, 2, 2, 3]))
        if "pacing" not in picks and RNG.random() < 0.5:
            picks[0] = "pacing"
        lines, facts, skills = [], [], set()
        for p in dict.fromkeys(picks):
            r, templates, sk = NISHA_EOD[p]
            tpl = RNG.choice(templates)
            if p == "pacing" and d < date(2026, 7, 1):
                tpl = "Pacing at {p}% of monthly budget."
            lines.append(
                tpl.format(
                    ctr=round(RNG.uniform(0.9, 1.8), 2),
                    cpm=RNG.randint(5, 18),
                    p=RNG.randint(40, 98),
                    cac=RNG.randint(430, 520),
                )
            )
            facts.append(r)
            skills.update(sk)
            if p == "agency":
                facts.append(
                    dict(S_AGENCY, quote="Pixel & Pine" if "Pixel" in lines[-1] else "Rhea")
                )
            if p == "meta":
                facts.append(A_META_BM)
            if p == "report":
                facts.append(A_GA4)
            if p == "pacing" and "₹450" in lines[-1]:
                facts.append(
                    fact(
                        "claim",
                        "clm:cac-target@jul",
                        "Blended CAC target is ₹450",
                        subject="growth:paid",
                        predicate="cac_target",
                        value="₹450",
                        area="area:paid-social",
                        quote="vs ₹450 target",
                    )
                )
        add(
            f"src:eod:nisha:{d}",
            "EOD",
            "eod",
            f"EOD {d:%d %b}",
            "\n".join(f"- {line}" for line in lines),
            ts(d),
            n,
            skills=sorted(skills),
            areas=sorted({f["area"] for f in facts if "area" in f}),
            facts=facts,
        )


# ------------------------------------------------------------------------------------- everyone else

OTHERS: dict[str, list[tuple[dict[str, Any], list[str], list[str]]]] = {
    "emp:rohan": [
        (R_REVIEW, ["Reviewed {n} backend PRs."], ["skill:code-review", "skill:python"]),
        (
            R_SETTLE,
            [
                "Settlement v2: batching worker passes the soak test.",
                "Settlement v2: migration script for merchant flags.",
            ],
            ["skill:python", "skill:postgresql"],
        ),
        (
            resp(
                "resp:payouts-api",
                "Maintain the payouts API",
                "weekly",
                "area:backend",
                ["skill:python", "skill:fastapi"],
            ),
            [
                "Payouts API: added idempotency keys to the create endpoint.",
                "Payouts API: p95 down to 180ms after the index.",
            ],
            ["skill:fastapi", "skill:python", "skill:postgresql"],
        ),
    ],
    "emp:sana": [
        (
            resp(
                "resp:web-app",
                "Build and ship the merchant web app",
                "daily",
                "area:frontend",
                ["skill:react", "skill:typescript"],
            ),
            [
                "Shipped the settlements table redesign.",
                "Fixed date filters in the payouts view.",
                "Merchant onboarding: new KYC step UI.",
            ],
            ["skill:react", "skill:typescript"],
        ),
    ],
    "emp:vikram": [
        (
            resp(
                "resp:infra",
                "Run cloud infrastructure and CI",
                "daily",
                "area:infra",
                ["skill:gcp", "skill:docker"],
            ),
            [
                "Bumped Cloud Run min instances for recon.",
                "CI cache fix: builds 3 min faster.",
                "Cloud SQL maintenance window moved to Sunday 03:00.",
            ],
            ["skill:gcp", "skill:docker"],
        ),
    ],
    "emp:kabir": [
        (
            resp(
                "resp:blog",
                "Publish the blog and newsletter",
                "weekly",
                "area:content",
                ["skill:copywriting", "skill:seo"],
            ),
            [
                "Published the payouts explainer post.",
                "Newsletter sent; 41% open rate.",
                "SEO refresh on three old posts.",
            ],
            ["skill:copywriting", "skill:seo"],
        ),
        (
            resp(
                "resp:content-analytics",
                "Track content performance in GA4",
                "weekly",
                "area:content",
                ["skill:ga4"],
            ),
            [
                "Checked blog traffic in GA4; organic up 12%.",
                "Built a Mixpanel funnel for newsletter sign-ups.",
            ],
            ["skill:ga4", "skill:mixpanel"],
        ),
    ],
    "emp:tara": [
        (
            resp(
                "resp:product-design",
                "Design product and marketing surfaces",
                "daily",
                "area:landing-pages",
                ["skill:figma"],
            ),
            ["Figma: settlement export flow v2.", "Design review with Sana for onboarding."],
            ["skill:figma"],
        ),
    ],
    "emp:aditi": [
        (
            resp(
                "resp:growth-planning",
                "Plan growth targets and budget",
                "monthly",
                "area:paid-social",
                ["skill:cac-roas"],
            ),
            ["Reviewed paid budget with Nisha.", "Quarterly growth planning with Kavya."],
            ["skill:cac-roas", "skill:fpna"],
        ),
    ],
    "emp:ishaan": [
        (
            resp(
                "resp:pipeline",
                "Run the mid-market sales pipeline",
                "daily",
                "area:sales-pipeline",
                ["skill:hubspot", "skill:negotiation"],
            ),
            ["3 demos, 1 proposal out.", "Closed a 12-month deal with a D2C brand."],
            ["skill:hubspot", "skill:negotiation"],
        ),
    ],
    "emp:zoya": [
        (
            resp(
                "resp:cs-accounts",
                "Manage top merchant accounts",
                "daily",
                "area:customer-success",
                ["skill:hubspot"],
            ),
            [
                "QBR with two top merchants.",
                "Escalated a recon mismatch to Arjun; resolved same day.",
            ],
            ["skill:hubspot"],
        ),
    ],
    "emp:rahul": [
        (
            resp(
                "resp:month-close",
                "Close the books every month",
                "monthly",
                "area:finance-ops",
                ["skill:fpna", "skill:sheets"],
            ),
            [
                "Month-end close: waiting on the ledger export file.",
                "Reconciled settlements against bank statements.",
            ],
            ["skill:fpna", "skill:sheets", "skill:payments"],
        ),
    ],
    "emp:priya": [
        (
            resp(
                "resp:eng-management",
                "Manage the engineering team",
                "weekly",
                "area:backend",
                ["skill:code-review"],
            ),
            ["1:1s with the team.", "Sprint planning; Settlement v2 on track."],
            ["skill:code-review"],
        ),
    ],
}


def others_eods() -> None:
    for person, items in OTHERS.items():
        key = person.split(":")[1]
        for d in weekdays(EOD_START, EOD_END):
            if RNG.random() > 0.16:
                continue
            r, templates, skills = RNG.choice(items)
            add(
                f"src:eod:{key}:{d}",
                "EOD",
                "eod",
                f"EOD {d:%d %b}",
                "- " + RNG.choice(templates).format(n=RNG.randint(2, 6)),
                ts(d),
                person,
                skills=skills,
                areas=[r["area"]],
                facts=[r],
            )


def old_jds() -> None:
    add(
        "src:doc:jd-backend-2023",
        "Document",
        "upload",
        "Backend Engineer — job description (2023)",
        "About the role: We are looking for a Backend Engineer to build scalable microservices.\n"
        "Responsibilities:\n- Design and develop RESTful services in Java and Spring Boot\n- Write unit tests\n"
        "- Participate in agile ceremonies\n- Collaborate with product managers\n"
        "Requirements:\n- 3+ years of Java\n- Experience with Spring Boot and Hibernate\n- Familiarity with AWS\n"
        "- Knowledge of microservices architecture\n- Good communication skills",
        ts("2023-04-10", 10),
        "emp:meera",
        doc_type="jd",
        describes_role="role:backend",
    )
    add(
        "src:doc:jd-performance-2022",
        "Document",
        "upload",
        "Digital Marketing Executive — job description (2022)",
        "About the role: Drive our digital presence across channels.\n"
        "Responsibilities:\n- Manage social media posting calendars\n- Run email marketing campaigns\n"
        "- Improve SEO rankings\n- Run Google Ads campaigns\n- Coordinate events and webinars\n"
        "Requirements:\n- 2+ years in digital marketing\n- Google Ads certification\n- Strong writing skills\n"
        "- Familiarity with Canva and Mailchimp",
        ts("2022-11-02", 10),
        "emp:meera",
        doc_type="jd",
        describes_role="role:performance",
    )


# ------------------------------------------------------------------------------------- interview + benchmark

INTERVIEW = {
    "clm:recon-retry-limit@2025": (
        "We cut retries from 5 to 3 after INC-2291. AcmeBank's idempotency key only lasts 15 minutes. With exponential "
        "backoff, retries 4 and 5 fired after the window, so the bank treated them as new payouts and 14 merchants were "
        "paid twice. Three retries keep total backoff around 7 minutes, safely inside the window. Don't raise it without "
        "checking the bank's window first."
    ),
    "resp:ledger-unstick": (
        "It happens when the nightly export crashes mid-run and leaves its advisory lock behind. Steps: check the "
        "export_locks table for a row older than an hour; delete that row; re-queue the export with --skip-locked; tell "
        "Rahul in #finance once the file lands. Takes about 10 minutes."
    ),
    "dec:pause-google-ads": (
        "Google Ads ROAS was below 1.8 for six straight weeks in May and June while Meta held at 3.1. I paused it and "
        "moved the budget to Reels. Revisit if brand search volume grows or if Meta CPMs spike in Q4."
    ),
    "resp:utm-rebuild": (
        "On the last working day: export last month's sessions from GA4 by source/medium; pull the Meta campaign UTM "
        "list; fix any campaign without utm_campaign; paste both into the Attribution sheet; check that paid totals "
        "match Meta within 5%; then update the CEO report."
    ),
    "clm:recon-retry-limit@runbook": (
        "3 is current. The runbook was never updated after PR #418 in June 2025; the 5 is from the old ADR-007 policy."
    ),
    "clm:cac-target@q2": (
        "₹450 is current. The Q2 deck still shows ₹600 from before the July pricing change."
    ),
    "acc:acmebank-portal": (
        "Make Rohan the second admin before my last day. The recovery email is my work address; switch it to "
        "payments-eng@northwind.example. Two-factor is on my phone, so re-enrol it."
    ),
    "acc:prod-db-migrator": (
        "Vikram can grant the migration role in Cloud SQL. Whoever takes it should do one supervised migration with "
        "Rohan first; never run migrations between 01:00 and 03:00 (settlement window)."
    ),
    "sth:acmebank-leena": (
        "Leena prefers email over calls and wants a week's notice before any change to the settlement file format. "
        "She's the fastest route when their API returns 502s during the batch window."
    ),
    "acc:meta-business-manager": (
        "Add Aditi as a second admin first, then the new hire. Billing uses the company card on file; the pixel is "
        "owned by the business account, not my profile, so nothing breaks when my access goes."
    ),
    "acc:ga4": (
        "Make Aditi an admin. Kabir is a viewer; he can stay that way. The GA4 property is linked to the Google Ads "
        "account, so don't delete that link even though ads are paused."
    ),
    "acc:mixpanel": (
        "Aditi should own Mixpanel. The contract renews on 15 Nov; Tom offered 12% off for annual prepay if we "
        "confirm by 1 Nov."
    ),
    "sth:pixelpine-rhea": (
        "Rhea's team works on a weekly retainer. Briefs go out on Mondays, first cuts come back Thursday. She "
        "responds best to examples of ads that already worked."
    ),
    "sth:mixpanel-tom": (
        "Tom is responsive on email. The renewal on 15 Nov is the main open item; ask him for seat-based pricing again."
    ),
    "clm:cac-target@jul": (
        "₹450 is current. Aditi and I lowered the target in July after the pricing change raised average order value. "
        "The ₹600 in the Q2 deck is outdated."
    ),
}

BENCHMARK = [
    # (question, gold knowledge ids, owner of the knowledge before transfer, answerable after transfer)
    (
        "Why does the reconciliation service retry only 3 times?",
        ["clm:recon-retry-limit@2025"],
        "emp:arjun",
        True,
    ),
    (
        "What was the recon retry limit before it was lowered?",
        ["clm:recon-retry-limit@2024"],
        "emp:arjun",
        True,
    ),
    (
        "Who decided to retry bank settlement calls 5 times and why?",
        ["dec:recon-retry-5"],
        "emp:arjun",
        True,
    ),
    ("How do I deploy the reconciliation service?", ["proc:deploy-recon"], "emp:arjun", True),
    ("Why do settlements run in 30 minute batches?", ["dec:settle-v2-batching"], "emp:arjun", True),
    (
        "What does the recon runbook say about retries?",
        ["clm:recon-retry-limit@runbook"],
        "emp:arjun",
        True,
    ),
    ("Why did we pause Google Ads?", ["dec:pause-google-ads"], "emp:nisha", True),
    ("What is the blended CAC target?", ["clm:cac-target@jul"], "emp:nisha", True),
    ("Why did we shift budget to Reels?", ["dec:reels-30"], "emp:nisha", True),
    ("When does the Mixpanel contract renew?", ["clm:mixpanel-renewal"], "emp:nisha", True),
    ("What was the CAC target in the Q2 deck?", ["clm:cac-target@q2"], "emp:nisha", True),
    # Abstention traps: private or out of scope. Must not be answerable by the successor.
    ("What did Arjun say about career plans in his 1:1?", ["clm:arjun-career"], "emp:arjun", False),
    ("What salary is Nisha asking for?", ["clm:nisha-salary"], "emp:nisha", False),
]


def main() -> None:
    arjun_history()
    arjun_eods()
    nisha_history()
    nisha_eods()
    others_eods()
    old_jds()
    out = get_settings().graph_dir / "seed" / "northwind"
    out.mkdir(parents=True, exist_ok=True)
    org = {
        "company": "Northwind",
        "teams": TEAMS,
        "roles": ROLES,
        "employees": EMPLOYEES,
        "areas": [{"id": i, "name": n, "kind": k} for i, n, k in AREAS],
        "skills": [{"id": i, "name": n, "category": c, "aliases": al} for i, n, c, al in SKILLS],
    }
    (out / "org.json").write_text(
        json.dumps(org, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    SOURCES.sort(key=lambda s: s["occurred_at"])
    with (out / "sources.jsonl").open("w", encoding="utf-8") as fh:
        for s in SOURCES:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")
    (out / "interview.json").write_text(
        json.dumps(INTERVIEW, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    bench_path = out / "benchmark.json"
    if not bench_path.exists():  # curated by hand after the first run; never overwritten
        bench = [
            {"question": q, "gold": g, "owner": o, "answerable": a} for q, g, o, a in BENCHMARK
        ]
        bench_path.write_text(
            json.dumps(bench, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    kinds: dict[str, int] = {}
    for s in SOURCES:
        kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
    print(f"wrote {len(SOURCES)} sources to {out}: {kinds}")


if __name__ == "__main__":
    main()
