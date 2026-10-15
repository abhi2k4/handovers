"""Upload anything: parse -> extract into the closed ontology -> resolve -> write or queue for review.

Tabular files that match a known template (EOD export, access inventory) map deterministically.
Prose (PDF, DOCX, PPTX, text, unknown tables) goes through MarkItDown and then LLM structured
extraction, or a rule-based extractor when no LLM is configured. Facts below the confidence bar wait
in a review queue and are not written to the graph until a person approves them.
"""

import io
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pandas as pd
from markitdown import MarkItDown
from rapidfuzz import fuzz, process

from core.clock import now_ms
from core.graph import Graph
from core.llm import LLM, LLMUnavailable
from ingestion.schema import AccessRole, Fact, SourceIn
from ingestion.writer import recompute_confidence, write_source

AUTO_ACCEPT = 0.75
TABLE_EXT = {".xlsx", ".xls", ".csv"}
MAX_CHARS = 14000


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=UTC).isoformat()


class Resolver:
    """Maps names, emails and titles to existing graph ids (closed world for people)."""

    def __init__(
        self,
        people: list[dict[str, Any]],
        titles: list[dict[str, Any]],
        skills: list[dict[str, Any]],
    ) -> None:
        self.people = people
        self.by_kind: dict[str, dict[str, str]] = {}
        for t in titles:
            self.by_kind.setdefault(t["kind"], {})[t["id"]] = t["title"]
        self.skills = skills

    def person(self, ref: str | None) -> str | None:
        if not ref:
            return None
        ref = ref.strip().lower()
        for p in self.people:
            if ref in (p["id"].lower(), (p.get("email") or "").lower(), p["name"].lower()):
                return str(p["id"])
        for p in self.people:
            if ref == p["name"].split()[0].lower():
                return str(p["id"])
        match = process.extractOne(
            ref, {p["id"]: p["name"].lower() for p in self.people}, scorer=fuzz.WRatio
        )
        return str(match[2]) if match and match[1] >= 88 else None

    def key(self, kind: str, title: str, prefix: str) -> str:
        existing = self.by_kind.get(kind, {})
        if existing:
            match = process.extractOne(
                title.lower(),
                {k: v.lower() for k, v in existing.items()},
                scorer=fuzz.token_set_ratio,
            )
            if match and match[1] >= 86:
                return str(match[2])
        return f"{prefix}:{_slug(title)}"

    def skill_ids(self, text: str) -> list[str]:
        low = text.lower()
        found = []
        for s in self.skills:
            terms = [str(a).lower() for a in (s.get("aliases") or [])] + [str(s["name"]).lower()]
            if any(re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", low) for t in terms if t):
                found.append(str(s["id"]))
        return found


async def resolver(graph: Graph) -> Resolver:
    people = await graph.read("people_directory", {})
    titles = await graph.read("catalog_titles", {})
    skills = await graph.read("skill_catalog", {})
    return Resolver(people, titles, skills)


# ---- parsing -------------------------------------------------------------------------------------


def read_table(name: str, data: bytes) -> pd.DataFrame | None:
    ext = Path(name).suffix.lower()
    try:
        if ext == ".csv":
            return pd.read_csv(io.BytesIO(data))
        if ext in (".xlsx", ".xls"):
            return pd.read_excel(io.BytesIO(data))
    except Exception:
        return None
    return None


def to_markdown(name: str, data: bytes) -> str:
    ext = Path(name).suffix.lower()
    if ext in (".txt", ".md"):
        return data.decode("utf-8", errors="replace")
    result = MarkItDown().convert_stream(io.BytesIO(data), file_extension=ext)
    return result.text_content or ""


def _col(df: pd.DataFrame, *names: str) -> str | None:
    cols = {c.lower().strip(): c for c in df.columns}
    for n in names:
        for low, original in cols.items():
            if low == n or low.startswith(n):
                return str(original)
    return None


# ---- extraction ----------------------------------------------------------------------------------

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": [
                            "responsibility",
                            "decision",
                            "procedure",
                            "claim",
                            "access",
                            "stakeholder",
                        ],
                    },
                    "title": {"type": "string"},
                    "person": {
                        "type": "string",
                        "description": "Name or email of the employee this is about",
                    },
                    "cadence": {
                        "type": "string",
                        "enum": ["daily", "weekly", "biweekly", "monthly", "quarterly", "adhoc"],
                    },
                    "rationale": {"type": "string"},
                    "steps": {"type": "array", "items": {"type": "string"}},
                    "subject": {"type": "string"},
                    "predicate": {"type": "string"},
                    "value": {"type": "string"},
                    "system": {"type": "string"},
                    "role": {"type": "string", "enum": ["admin", "owner", "editor", "member"]},
                    "org": {"type": "string"},
                    "stakeholder_kind": {
                        "type": "string",
                        "enum": ["vendor", "client", "agency", "partner"],
                    },
                    "context": {"type": "string"},
                    "quote": {
                        "type": "string",
                        "description": "Exact supporting text from the document",
                    },
                    "confidence": {"type": "number"},
                },
                "required": ["kind", "title", "quote", "confidence"],
            },
        }
    },
    "required": ["facts"],
}

EXTRACT_SYSTEM = (
    "You extract facts about people's work from company documents into a fixed schema. Only extract what the "
    "text states. Kinds: responsibility (an ongoing duty, with cadence), decision (a choice plus its reason), "
    "procedure (ordered steps), claim (a setting, target or date: subject/predicate/value), access (an account "
    "or tool someone administers), stakeholder (an external person someone works with, with their org). "
    'Titles must be specific: a responsibility starts with a verb and names its object ("Run quarterly business '
    "reviews for the top 10 merchants\"); a stakeholder's title is the person's name and org is their company; a "
    "decision's title states the choice and its rationale says why. Every fact needs an exact quote from the text "
    "and a confidence between 0 and 1. Never extract opinions about performance, health, salary or personal life."
)


def _to_fact(
    raw: dict[str, Any], res: Resolver, default_person: str | None, text: str
) -> tuple[Fact | None, str | None]:
    kind, title = raw.get("kind"), (raw.get("title") or "").strip()
    if not kind or not title:
        return None, None
    person = res.person(raw.get("person")) or default_person
    quote = (raw.get("quote") or "").strip()
    conf = float(raw.get("confidence") or 0.5)
    if quote and quote.lower()[:30] not in text.lower():
        conf = min(conf, 0.5)  # unverifiable quote: never auto-accept
    prefix = {
        "responsibility": "resp",
        "decision": "dec",
        "procedure": "proc",
        "claim": "clm",
        "access": "acc",
        "stakeholder": "sth",
    }[kind]
    kind_for_key = {
        "responsibility": "Responsibility",
        "access": "Account",
        "stakeholder": "Stakeholder",
    }.get(kind, "Knowledge")
    key = res.key(kind_for_key, title, prefix)
    fact = Fact(
        kind=kind,
        key=key,
        title=title,
        people=[person] if person else [],
        quote=quote or None,
        confidence=conf,
        cadence=raw.get("cadence"),
        rationale=raw.get("rationale"),
        steps=raw.get("steps") or [],
        subject=raw.get("subject"),
        predicate=raw.get("predicate"),
        value=raw.get("value"),
        system=raw.get("system"),
        role=raw.get("role"),
        org=raw.get("org"),
        stakeholder_kind=raw.get("stakeholder_kind"),
        context=raw.get("context"),
        skills=res.skill_ids(f"{title} {quote}") if kind == "responsibility" else [],
    )
    return fact, person


RESP_PATTERN = re.compile(
    r"(?:responsible for|owns?|manages?|handles?|runs?|maintains?)\s+(?:the\s+)?([^.;\n]{8,90})",
    re.IGNORECASE,
)


def rule_extract(text: str, res: Resolver, person: str | None) -> list[Fact]:
    """Fallback without an LLM: duty sentences become proposed responsibilities (sent to review)."""
    facts: list[Fact] = []
    for m in RESP_PATTERN.finditer(text):
        phrase = m.group(1).strip(" ,:-")
        title = phrase[0].upper() + phrase[1:]
        facts.append(
            Fact(
                kind="responsibility",
                key=res.key("Responsibility", title, "resp"),
                title=title,
                people=[person] if person else [],
                quote=m.group(0)[:200],
                confidence=0.55,
                skills=res.skill_ids(phrase),
            )
        )
    return facts[:15]


async def llm_extract(llm: LLM, text: str, res: Resolver, person: str | None) -> list[Fact]:
    out = await llm.json(EXTRACT_SYSTEM, f"Document:\n{text[:MAX_CHARS]}", EXTRACT_SCHEMA)
    facts = []
    for raw in out.get("facts", []):
        f, _ = _to_fact(raw, res, person, text)
        if f:
            facts.append(f)
    return facts


# ---- templates -----------------------------------------------------------------------------------


def access_inventory(df: pd.DataFrame, res: Resolver, name: str) -> list[SourceIn] | None:
    tool, owner = (
        _col(df, "tool", "system", "account", "app"),
        _col(df, "owner", "admin", "email", "person"),
    )
    if not tool or not owner:
        return None
    role_col, renew_col = _col(df, "role", "access"), _col(df, "renew", "renewal")
    facts = []
    for _, row in df.iterrows():
        person = res.person(str(row[owner]))
        if not person or pd.isna(row[tool]):
            continue
        title = str(row[tool]).strip()
        role = (
            str(row[role_col]).strip().lower()
            if role_col and not pd.isna(row[role_col])
            else "admin"
        )
        facts.append(
            Fact(
                kind="access",
                key=res.key("Account", title, "acc"),
                title=title,
                system=title.split()[0],
                role=cast(
                    AccessRole, role if role in ("admin", "owner", "editor", "member") else "admin"
                ),
                people=[person],
                quote=f"{title}: {row[owner]}",
                confidence=0.95,
            )
        )
        if renew_col and not pd.isna(row[renew_col]):
            facts.append(
                Fact(
                    kind="claim",
                    key=f"clm:{_slug(title)}-renewal",
                    title=f"{title} renews on {row[renew_col]}",
                    subject=f"tool:{_slug(title)}",
                    predicate="renewal_date",
                    value=str(row[renew_col]),
                    people=[person],
                    confidence=0.95,
                )
            )
    now = now_ms()
    return [
        SourceIn(
            id=f"src:upload:{uuid.uuid4().hex[:10]}",
            kind="Upload",
            system="upload",
            title=name,
            text=df.to_csv(index=False)[:MAX_CHARS],
            occurred_at=_iso(now),
            facts=facts,
        )
    ]


def eod_export(
    df: pd.DataFrame, res: Resolver, name: str, default_person: str | None
) -> list[tuple[SourceIn, str | None]] | None:
    date_col, text_col = (
        _col(df, "date", "day"),
        _col(df, "update", "summary", "eod", "work", "notes"),
    )
    if not date_col or not text_col:
        return None
    who_col = _col(df, "employee", "email", "name", "person")
    out = []
    for _, row in df.iterrows():
        if pd.isna(row[text_col]):
            continue
        person = res.person(str(row[who_col])) if who_col else default_person
        when = pd.to_datetime(row[date_col], errors="coerce")
        at = (
            when.to_pydatetime().replace(tzinfo=UTC) if not pd.isna(when) else datetime.now(UTC)
        ).isoformat()
        text = str(row[text_col])
        out.append(
            (
                SourceIn(
                    id=f"src:upload:{uuid.uuid4().hex[:10]}",
                    kind="EOD",
                    system="upload",
                    title=f"EOD {str(row[date_col])[:10]}",
                    text=text,
                    occurred_at=at,
                    author=person,
                    skills=res.skill_ids(text),
                ),
                person,
            )
        )
    return out


# ---- entry point ---------------------------------------------------------------------------------


async def extract(llm: LLM, text: str, res: Resolver, person: str | None) -> tuple[list[Fact], str]:
    """Facts from free text: the LLM when configured, otherwise (or when it fails) the rules."""
    if llm.enabled:
        try:
            return await llm_extract(llm, text, res, person), llm.model
        except LLMUnavailable:
            pass
    return rule_extract(text, res, person), "rules"


async def store(
    graph: Graph, sources: list[SourceIn], *, origin: str, employee: str | None = None
) -> tuple[int, int]:
    """The review gate shared by uploads and connectors.

    Confident facts about a known person are written; the rest wait in the review queue and never
    reach the graph until someone approves them. Returns (facts written, facts queued).
    """
    now = now_ms()
    written, queued = 0, 0
    for src in sources:
        accepted = [f for f in src.facts if f.confidence >= AUTO_ACCEPT and f.people]
        pending = [f for f in src.facts if f not in accepted]
        src.facts = accepted
        await write_source(graph, src, origin=origin)
        written += len(accepted)
        for f in pending:
            await graph.run(
                "review_add",
                {
                    "id": f"rev:{uuid.uuid4().hex[:10]}",
                    "source": src.id,
                    "fact": f.model_dump_json(),
                    "kind": f.kind,
                    "title": f.title,
                    "confidence": f.confidence,
                    "employee": (f.people or [employee or src.author or ""])[0],
                    "now": now,
                },
            )
            queued += 1
    await recompute_confidence(graph)
    return written, queued


async def ingest(
    graph: Graph, llm: LLM, name: str, data: bytes, employee: str | None
) -> dict[str, Any]:
    res = await resolver(graph)
    now = now_ms()
    ext = Path(name).suffix.lower()
    sources: list[SourceIn] = []
    method = "template"
    if ext in TABLE_EXT and (df := read_table(name, data)) is not None:
        inv = access_inventory(df, res, name)
        if inv:
            sources = inv
        else:
            eods = eod_export(df, res, name, employee)
            if eods:
                method = llm.model if llm.enabled else "rules"
                for src, person in eods:
                    try:
                        src.facts = (
                            await llm_extract(llm, src.text, res, person)
                            if llm.enabled
                            else rule_extract(src.text, res, person)
                        )
                    except LLMUnavailable:
                        src.facts = rule_extract(src.text, res, person)
                    sources.append(src)
    if not sources:
        text = to_markdown(name, data).strip()
        if not text:
            raise ValueError("Couldn't read any text from this file.")
        try:
            facts = await llm_extract(llm, text, res, employee)
            method = llm.model
        except LLMUnavailable:
            facts, method = rule_extract(text, res, employee), "rules"
        sources = [
            SourceIn(
                id=f"src:upload:{uuid.uuid4().hex[:10]}",
                kind="Upload",
                system="upload",
                title=name,
                text=text[:MAX_CHARS],
                occurred_at=_iso(now),
                author=employee,
                skills=res.skill_ids(text),
                facts=facts,
            )
        ]
    written, queued = await store(graph, sources, origin="upload", employee=employee)
    return {
        "file": name,
        "sources": len(sources),
        "written": written,
        "review": queued,
        "method": method,
    }


async def decide_review(
    graph: Graph, review_id: str, approve: bool, employee: str | None = None
) -> dict[str, Any]:
    item = await graph.one("review_get", {"id": review_id})
    if not item or item["status"] != "pending":
        raise KeyError(review_id)
    if approve:
        fact = Fact.model_validate(json.loads(item["fact"]))
        if not fact.people and employee:
            fact.people = [employee]
        if not fact.people:
            raise ValueError("Pick whose work this is before approving.")
        src_row = await graph.one("source_get", {"id": item["source_id"]})
        src = SourceIn(
            id=item["source_id"],
            kind=(src_row or {}).get("kind") or "Upload",
            system="upload",
            title=(src_row or {}).get("title") or "Upload",
            text=(src_row or {}).get("text") or "",
            occurred_at=_iso((src_row or {}).get("occurred_at") or now_ms()),
            facts=[fact],
        )
        await write_source(graph, src, origin="upload")
        await recompute_confidence(graph)
    await graph.run(
        "review_set_status",
        {"id": review_id, "status": "approved" if approve else "rejected", "now": now_ms()},
    )
    return {"id": review_id, "status": "approved" if approve else "rejected"}
