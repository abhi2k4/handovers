"""Write sources and their facts into the graph with fixed, parameterised Cypher.

This is the single path into the graph for seed fixtures, connector payloads, uploads and interview
answers. It never creates node or relationship types outside the closed ontology.
"""

from dataclasses import dataclass, field
from typing import Any

from core.clock import OPEN, now_ms, to_ms
from core.graph import Graph
from ingestion.schema import SOURCE_QUALITY, Fact, Org, SourceIn

KNOWLEDGE_KIND = {"decision": "Decision", "procedure": "Procedure", "claim": "Claim"}
NOT_DOCUMENTATION = {"notes", "jd"}


@dataclass
class WriteStats:
    sources: int = 0
    facts: int = 0
    by_kind: dict[str, int] = field(default_factory=dict)

    def add(self, kind: str) -> None:
        self.facts += 1
        self.by_kind[kind] = self.by_kind.get(kind, 0) + 1


async def write_org(graph: Graph, org: Org) -> None:
    now = now_ms()
    for t in org.teams:
        await graph.run("org_upsert_team", {"id": t["id"], "name": t["name"]})
    for r in org.roles:
        await graph.run("org_upsert_role", {"id": r["id"], "title": r["title"]})
    for a in org.areas:
        await graph.run(
            "org_upsert_area", {"id": a["id"], "name": a["name"], "kind": a.get("kind", "area")}
        )
    for s in org.skills:
        await graph.run(
            "org_upsert_skill",
            {
                "id": s["id"],
                "name": s["name"],
                "category": s.get("category", "skill"),
                "aliases": s.get("aliases", []),
            },
        )
    for e in org.employees:
        await graph.run(
            "org_upsert_employee",
            {
                "id": e.id,
                "name": e.name,
                "email": e.email,
                "title": e.title,
                "status": e.status,
                "team": e.team,
                "role": e.role,
                "joined_at": to_ms(e.joined_at),
                "open": OPEN,
                "now": now,
            },
        )
    for e in org.employees:
        if e.manager:
            await graph.run("org_set_manager", {"id": e.id, "manager": e.manager})


def knowledge_text(f: Fact) -> str:
    parts = [
        f.title,
        f.rationale or "",
        f.value or "",
        " ".join(f.steps),
        " ".join(f.alternatives),
        f.quote or "",
    ]
    return " ".join(p for p in parts if p).strip()


async def write_source(
    graph: Graph, src: SourceIn, *, origin: str, stats: WriteStats | None = None
) -> WriteStats:
    stats = stats or WriteStats()
    now = now_ms()
    at = to_ms(src.occurred_at)
    await graph.run(
        "source_upsert",
        {
            "id": src.id,
            "kind": src.kind,
            "system": src.system,
            "title": src.title,
            "text": src.text,
            "occurred_at": at,
            "sensitivity": src.sensitivity,
            "quality": SOURCE_QUALITY.get(src.kind, 0.5),
            "url": src.url,
            "status": src.status,
            "doc_type": src.doc_type,
            "origin": origin,
            "now": now,
            "areas": src.areas,
            "skills": src.skills,
            "author": src.author or "",
        },
        label=src.kind,
    )
    if src.attendees:
        await graph.run("source_link_attendees", {"id": src.id, "attendees": src.attendees})
    if src.describes_role:
        await graph.run("source_describes_role", {"id": src.id, "role": src.describes_role})
    stats.sources += 1

    default_people = [p for p in [src.author, *src.attendees] if p]
    documented = (
        src.kind == "Document" and src.doc_type not in NOT_DOCUMENTATION
    ) or src.kind == "InterviewAnswer"
    for f in src.facts:
        await write_fact(
            graph,
            src,
            f,
            at=at,
            now=now,
            origin=origin,
            people=f.people or default_people,
            documented=documented,
        )
        stats.add(f.kind)
    return stats


async def write_fact(
    graph: Graph,
    src: SourceIn,
    f: Fact,
    *,
    at: int,
    now: int,
    origin: str,
    people: list[str],
    documented: bool,
) -> None:
    base: dict[str, Any] = {
        "source": src.id,
        "key": f.key,
        "title": f.title,
        "quote": f.quote,
        "occurred_at": at,
        "open": OPEN,
        "now": now,
        "origin": origin,
        "people": people,
        "areas": [f.area] if f.area else [],
    }
    if f.kind == "responsibility":
        await graph.run("fact_responsibility", {**base, "cadence": f.cadence, "skills": f.skills})
    elif f.kind == "access":
        await graph.run("fact_access", {**base, "system": f.system, "role": f.role})
    elif f.kind == "stakeholder":
        await graph.run(
            "fact_stakeholder",
            {**base, "org": f.org, "stakeholder_kind": f.stakeholder_kind, "context": f.context},
        )
    elif f.kind == "skill":
        await graph.run("fact_skill", {**base, "category": f.category})
    else:
        label = KNOWLEDGE_KIND[f.kind]
        await graph.run(
            "fact_knowledge",
            {
                **base,
                "kind": label,
                "valid_from": at,
                "sensitivity": src.sensitivity,
                "rationale": f.rationale,
                "alternatives": f.alternatives,
                "steps": f.steps,
                "handles": f.handles,
                "subject": f.subject,
                "predicate": f.predicate,
                "value": f.value,
                "text": knowledge_text(f),
                "documented": documented,
            },
            label=label,
        )
        if f.supersedes:
            await graph.run("knowledge_supersede", {"new": f.key, "old": f.supersedes})
        if f.justified_by:
            await graph.run("knowledge_justify", {"id": f.key, "decision": f.justified_by})


async def recompute_confidence(graph: Graph) -> int:
    rows = await graph.run("knowledge_confidence", {})
    return int(rows[0]["updated"]) if rows else 0
