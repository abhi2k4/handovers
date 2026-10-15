"""The four HR outputs, generated from the graph.

Shape for each: graph queries produce the facts -> a fixed structure holds them -> the LLM (if
configured) only rewrites wording -> every item keeps the id of the evidence behind it.
"""

import json
import re
from functools import lru_cache
from typing import Any

from rapidfuzz import fuzz

from core.clock import now_ms
from core.config import get_settings
from core.graph import Graph
from core.llm import LLM, LLMUnavailable
from services import analysis, policy

CADENCE_WORD = {
    "daily": "daily",
    "weekly": "weekly",
    "biweekly": "every two weeks",
    "monthly": "monthly",
    "quarterly": "quarterly",
    "adhoc": "as needed",
}


# Boilerplate that says nothing about the actual job; never flagged in the old-JD diff.
GENERIC_JD_PHRASES = (
    "communication",
    "collaborat",
    "agile",
    "ceremon",
    "writing skills",
    "team player",
    "self-starter",
)


@lru_cache
def interview_bank() -> dict[str, dict[str, Any]]:
    path = get_settings().graph_dir / "seed" / "interview_bank.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


async def skill_catalog(graph: Graph) -> dict[str, dict[str, Any]]:
    return {r["id"]: r for r in await graph.read("skill_catalog", {})}


def _requirements(p: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Must-have = strongly evidenced, or needed by work only this person does. Nice = the rest."""
    eods = max(p.get("eod_total") or 0, 1)
    sole_skill_ids = {
        sid
        for r in p["responsibilities"]
        if not r["co_owners"]
        for sid in (r.get("skill_ids") or [])
    }
    must, nice = [], []
    for s in p["skills"]:
        strong = s["evidence"] >= max(5, int(eods * 0.15))
        if strong or (s["id"] in sole_skill_ids and s["evidence"] >= 2):
            must.append(s)
        elif s["evidence"] >= 2:
            nice.append(s)
    return must[:6], nice[:5]


def _old_jd_diff(
    p: dict[str, Any], old: dict[str, Any] | None, catalog: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    if not old or not old.get("text"):
        return {"old_title": None, "missing": [], "unused": []}
    text = old["text"]
    lower = text.lower()
    lines = [ln.strip("- ").strip() for ln in text.splitlines() if ln.strip().startswith("-")]

    def aliases(skill_ids: list[str]) -> list[str]:
        out: list[str] = []
        for sid in skill_ids:
            c = catalog.get(sid) or {}
            out += [str(a).lower() for a in (c.get("aliases") or [])] + [
                str(c.get("name", "")).lower()
            ]
        return [a for a in out if a]

    missing = []
    for r in p["responsibilities"]:
        mentioned = any(fuzz.token_set_ratio(r["title"].lower(), ln.lower()) >= 62 for ln in lines)
        skill_hit = any(
            re.search(rf"\b{re.escape(a)}\b", lower) for a in aliases(r.get("skill_ids") or [])
        )
        if not mentioned and not skill_hit:
            missing.append({"id": r["id"], "title": r["title"]})
    used_terms = aliases([s["id"] for s in p["skills"] if s["evidence"] >= 2])
    used_terms += [r["title"].lower() for r in p["responsibilities"]]
    unused = []
    for ln in lines:
        low = ln.lower()
        if any(g in low for g in GENERIC_JD_PHRASES):
            continue
        hit = any(re.search(rf"\b{re.escape(t)}\b", low) for t in used_terms if len(t) > 2)
        close = any(
            fuzz.token_set_ratio(low, r["title"].lower()) >= 62 for r in p["responsibilities"]
        )
        if not hit and not close:
            unused.append(ln)
    return {
        "old_title": old.get("title"),
        "old_id": old.get("id"),
        "missing": missing,
        "unused": unused,
    }


async def build_jd(graph: Graph, llm: LLM, emp: str) -> dict[str, Any]:
    p = await analysis.person(graph, emp)
    if p is None:
        raise KeyError(emp)
    catalog = await skill_catalog(graph)
    must, nice = _requirements(p)
    old = await graph.one("role_old_jd", {"emp": emp})
    responsibilities = [
        {
            "id": r["id"],
            "text": r["title"],
            "cadence": r.get("cadence"),
            "share": r["share"],
            "evidence": r["evidence"],
            "sole": not r["co_owners"],
            "with": r["co_owners"],
        }
        for r in p["responsibilities"]
        if r["evidence"] > 0 or not r["co_owners"]
    ]
    tools = [s["name"] for s in p["skills"] if s["category"] == "tool" and s["evidence"] >= 2]
    stakeholders = [
        {"id": s["id"], "name": s["name"], "org": s.get("org"), "context": s.get("context")}
        for s in p["stakeholders"]
    ]
    accounts = [
        {"id": a["id"], "name": a["name"], "role": a["role"]}
        for a in p["accounts"]
        if a["role"] in ("admin", "owner")
    ]
    top = [r["text"].lower() for r in responsibilities[:2]]
    summary = (
        f"{p['title']} on the {p['team']} team, reporting to {p.get('manager') or 'the founder'}. "
        f"Most of the work is to {top[0]}" + (f" and {top[1]}." if len(top) > 1 else ".")
        if top
        else f"{p['title']} on the {p['team']} team."
    )
    jd: dict[str, Any] = {
        "employee_id": emp,
        "role": p.get("role") or p["title"],
        "title": p["title"],
        "team": p["team"],
        "reports_to": p.get("manager"),
        "summary": summary,
        "responsibilities": responsibilities,
        "must": [{"id": s["id"], "name": s["name"], "evidence": s["evidence"]} for s in must],
        "nice": [{"id": s["id"], "name": s["name"], "evidence": s["evidence"]} for s in nice],
        "tools": tools,
        "stakeholders": stakeholders,
        "accounts": accounts,
        "evidence_total": p["sources"],
        "eod_total": p["eod_total"],
        "diff": _old_jd_diff(p, old, catalog),
        "phrased_by": "template",
    }
    try:
        phrased = await llm.json(
            "You write job descriptions for a hiring team. Use ONLY the facts given. Never invent tools, "
            "duties, numbers or benefits. Plain, specific language; no buzzwords, no exclamation marks.",
            "Facts about the role, learned from the previous person's actual work:\n"
            + json.dumps(
                {
                    k: jd[k]
                    for k in (
                        "title",
                        "team",
                        "reports_to",
                        "responsibilities",
                        "must",
                        "nice",
                        "tools",
                        "stakeholders",
                    )
                }
            )
            + "\n\nReturn: a two-sentence summary of the role, and for every responsibility id a concise "
            "bullet starting with a verb (max 14 words). Keep ids unchanged.",
            {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "bullets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"id": {"type": "string"}, "text": {"type": "string"}},
                            "required": ["id", "text"],
                        },
                    },
                },
                "required": ["summary", "bullets"],
            },
        )
        by_id = {
            b["id"]: b["text"] for b in phrased.get("bullets", []) if b.get("id") and b.get("text")
        }
        for r in jd["responsibilities"]:
            r["text"] = by_id.get(r["id"], r["text"])
        if phrased.get("summary"):
            jd["summary"] = phrased["summary"]
        jd["phrased_by"] = llm.model
    except LLMUnavailable:
        pass
    return jd


# ---- screening kit -------------------------------------------------------------------------------


async def build_screening(graph: Graph, llm: LLM, emp: str) -> dict[str, Any]:
    p = await analysis.person(graph, emp)
    if p is None:
        raise KeyError(emp)
    catalog = await skill_catalog(graph)
    must, nice = _requirements(p)
    eods = max(p["eod_total"], 1)
    criteria: list[dict[str, Any]] = []
    for s in must:
        c = catalog.get(s["id"], {})
        criteria.append(
            {
                "id": s["id"],
                "label": f"Hands-on {s['name']}",
                "level": "must",
                "why": f"Shows up in {s['evidence']} of {p['sources']} work records",
                "signals": [str(a) for a in (c.get("aliases") or [])][:8] or [s["name"].lower()],
            }
        )
    for r in [r for r in p["responsibilities"] if not r["co_owners"]][:3]:
        sigs: list[str] = []
        for sid in r.get("skill_ids") or []:
            sigs += [str(a) for a in (catalog.get(sid, {}).get("aliases") or [])][:4]
        criteria.append(
            {
                "id": r["id"],
                "label": f"Has done: {r['title'][0].lower() + r['title'][1:]}",
                "level": "must",
                "why": "Only this person does it today"
                + (
                    f" ({CADENCE_WORD.get(r.get('cadence') or '', '')})" if r.get("cadence") else ""
                ),
                "signals": sigs[:8],
            }
        )
    for s in nice:
        c = catalog.get(s["id"], {})
        criteria.append(
            {
                "id": s["id"],
                "label": s["name"],
                "level": "nice",
                "why": f"Used occasionally ({s['evidence']} records)",
                "signals": [str(a) for a in (c.get("aliases") or [])][:8] or [s["name"].lower()],
            }
        )
    return {"employee_id": emp, "title": p["title"], "criteria": criteria, "eod_total": eods}


def _snippet(text: str, start: int, end: int) -> str:
    lo, hi = max(0, start - 60), min(len(text), end + 60)
    return (
        ("…" if lo else "")
        + text[lo:hi].replace("\n", " ").strip()
        + ("…" if hi < len(text) else "")
    )


def check_resume_rules(resume: str, criteria: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deterministic matcher: a signal found => meets; nothing found => missing.

    Returns per-criterion verdicts only. There is deliberately no overall score or ranking.
    """
    low = resume.lower()
    out = []
    for c in criteria:
        found = None
        for sig in c.get("signals") or []:
            m = re.search(rf"(?<![a-z0-9]){re.escape(sig.lower())}(?![a-z0-9])", low)
            if m:
                found = (sig, m.start(), m.end())
                break
        if found:
            verdict, quote = "meets", _snippet(resume, found[1], found[2])
        else:
            verdict, quote = (
                ("unclear" if c["level"] == "must" and c["id"].startswith("resp:") else "missing"),
                None,
            )
        out.append(
            {
                "id": c["id"],
                "label": c["label"],
                "level": c["level"],
                "verdict": verdict,
                "quote": quote,
                "ask": None
                if verdict == "meets"
                else f"Ask: tell me about a time you worked with {c['label'].replace('Has done: ', '').replace('Hands-on ', '')}.",
            }
        )
    return out


async def check_resume(graph: Graph, llm: LLM, emp: str, resume: str) -> dict[str, Any]:
    kit = await build_screening(graph, llm, emp)
    verdicts = check_resume_rules(resume, kit["criteria"])
    method = "rules"
    try:
        judged = await llm.json(
            "You compare a resume against hiring criteria. For each criterion decide meets / unclear / missing. "
            "Say meets only when a resume sentence directly shows that criterion, and quote that sentence exactly. "
            "Related but different experience is unclear. Do not score or rank the candidate overall. "
            "If unclear or missing, suggest one short phone-screen question.",
            "Criteria:\n"
            + json.dumps([{k: c[k] for k in ("id", "label", "level")} for c in kit["criteria"]])
            + "\n\nResume:\n"
            + resume[:12000],
            {
                "type": "object",
                "properties": {
                    "verdicts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "verdict": {
                                    "type": "string",
                                    "enum": ["meets", "unclear", "missing"],
                                },
                                "quote": {"type": "string"},
                                "ask": {"type": "string"},
                            },
                            "required": ["id", "verdict"],
                        },
                    }
                },
                "required": ["verdicts"],
            },
        )
        by_id = {v["id"]: v for v in judged.get("verdicts", [])}
        for v in verdicts:
            j = by_id.get(v["id"])
            if not j:
                continue
            quote = (j.get("quote") or "").strip()
            # Accept a "meets" only if the quote really appears in the resume, and for "has done"
            # criteria only if the quote contains one of the criterion's signals.
            signals = [
                s.lower()
                for s in next((c["signals"] for c in kit["criteria"] if c["id"] == v["id"]), [])
            ]
            grounded = not v["id"].startswith("resp:") or any(
                sig in quote.lower() for sig in signals
            )
            if (
                j["verdict"] == "meets"
                and quote
                and quote.lower()[:40] in resume.lower()
                and grounded
            ):
                v["verdict"], v["quote"], v["ask"] = "meets", quote, None
            elif j["verdict"] in ("unclear", "missing") and v["verdict"] != "meets":
                v["verdict"], v["ask"] = j["verdict"], j.get("ask") or v["ask"]
        method = llm.model
    except LLMUnavailable:
        pass
    counts = {
        k: sum(1 for v in verdicts if v["verdict"] == k) for k in ("meets", "unclear", "missing")
    }
    must_missing = [
        v["label"] for v in verdicts if v["level"] == "must" and v["verdict"] == "missing"
    ]
    return {"verdicts": verdicts, "counts": counts, "must_missing": must_missing, "method": method}


# ---- interview kit -------------------------------------------------------------------------------


async def build_interview_kit(graph: Graph, llm: LLM, emp: str) -> dict[str, Any]:
    p = await analysis.person(graph, emp)
    if p is None:
        raise KeyError(emp)
    must, _ = _requirements(p)
    bank = interview_bank()
    items = []
    for s in must:
        b = bank.get(s["id"])
        if not b:
            continue
        work = [r["title"] for r in p["responsibilities"] if s["id"] in (r.get("skill_ids") or [])][
            :2
        ]
        items.append(
            {
                "id": s["id"],
                "skill": s["name"],
                "question": b["question"],
                "listen_for": b["listen_for"],
                "red_flags": b["red_flags"],
                "context": "Here this is used for: " + "; ".join(w[0].lower() + w[1:] for w in work)
                if work
                else "",
            }
        )
    kit: dict[str, Any] = {
        "employee_id": emp,
        "title": p["title"],
        "questions": items,
        "phrased_by": "bank",
    }
    try:
        phrased = await llm.json(
            "You help a non-technical HR person screen candidates. Rewrite each question so it is grounded in "
            "this company's real work (given as context), stays answerable by any qualified candidate, and can "
            "be judged by someone who is not an expert. Keep ids. Keep listen_for and red_flags short and plain.",
            json.dumps(
                [
                    {
                        k: i[k]
                        for k in ("id", "skill", "question", "listen_for", "red_flags", "context")
                    }
                    for i in items
                ]
            ),
            {
                "type": "object",
                "properties": {
                    "questions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "question": {"type": "string"},
                                "listen_for": {"type": "array", "items": {"type": "string"}},
                                "red_flags": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["id", "question", "listen_for", "red_flags"],
                        },
                    }
                },
                "required": ["questions"],
            },
        )
        by_id = {q["id"]: q for q in phrased.get("questions", [])}
        for i in items:
            q = by_id.get(i["id"])
            if q:
                i["question"], i["listen_for"], i["red_flags"] = (
                    q["question"],
                    q["listen_for"][:4],
                    q["red_flags"][:3],
                )
        kit["phrased_by"] = llm.model
    except LLMUnavailable:
        pass
    return kit


# ---- handover plan -------------------------------------------------------------------------------


async def build_plan(
    graph: Graph, emp: str, successor: dict[str, Any] | None, gaps: list[dict[str, Any]]
) -> dict[str, Any]:
    p = await analysis.person(graph, emp)
    if p is None:
        raise KeyError(emp)
    now = now_ms()

    async def receiver(skill_ids: list[str]) -> dict[str, Any] | None:
        if successor and successor.get("id"):
            return {"id": successor["id"], "name": successor["name"], "why": "Successor"}
        if not skill_ids:
            return None
        rows = await graph.read("receivers_by_skill", {"emp": emp, "skills": skill_ids})
        if rows:
            return {
                "id": rows[0]["id"],
                "name": rows[0]["name"],
                "why": f"Most evidence of the skills ({rows[0]['strength']})",
            }
        return None

    gap_by_target = {g["target_id"]: g for g in gaps}
    sections: list[dict[str, Any]] = []

    access = []
    for a in p["accounts"]:
        if a["role"] in ("admin", "owner") and not a["other_admins"]:
            g = gap_by_target.get(a["id"])
            access.append(
                {
                    "id": a["id"],
                    "title": f"Add a second admin to {a['name']}",
                    "detail": (g or {}).get("answer")
                    or f"{p['name'].split()[0]} is the only {a['role']}.",
                    "receiver": await receiver([]),
                    "urgent": True,
                }
            )
    sections.append({"key": "access", "title": "Access to hand over first", "items": access})

    open_work = [
        {
            "id": t["id"],
            "title": t["title"],
            "detail": "Open",
            "receiver": await receiver([]),
            "urgent": False,
        }
        for t in p["open_work"]
    ]
    sections.append({"key": "open", "title": "Open work", "items": open_work})

    recurring = []
    for r in sorted(p["responsibilities"], key=lambda r: r.get("next_due") or 0):
        if r.get("co_owners"):
            continue
        cadence = CADENCE_WORD.get(r.get("cadence") or "", "")
        recurring.append(
            {
                "id": r["id"],
                "title": r["title"],
                "detail": " · ".join(
                    x
                    for x in [
                        cadence.capitalize(),
                        f"{round(r['share'] * 100)}% of logged work" if r["share"] else "",
                    ]
                    if x
                ),
                "due": r.get("next_due"),
                "overdue": r.get("overdue"),
                "receiver": await receiver(r.get("skill_ids") or []),
                "urgent": bool(r.get("overdue")),
            }
        )
    sections.append(
        {"key": "recurring", "title": "Recurring work only they do", "items": recurring}
    )

    relations = []
    for s in p["stakeholders"]:
        if s["other_contacts"]:
            continue
        g = gap_by_target.get(s["id"])
        relations.append(
            {
                "id": s["id"],
                "title": f"Introduce the successor to {s['name']} ({s.get('org')})",
                "detail": (g or {}).get("answer") or s.get("context") or "",
                "receiver": await receiver([]),
                "urgent": False,
            }
        )
    sections.append(
        {"key": "relationships", "title": "Relationships to introduce", "items": relations}
    )

    capture = [
        {
            "id": g["id"],
            "title": g["title"],
            "detail": policy.RULE_LABEL.get(g["rule"], g["rule"]),
            "status": g["status"],
            "urgent": g["status"] == "open",
        }
        for g in gaps
        if g["rule"] in policy.INTERVIEW_RULES and g["rule"] not in ("G7A", "G7S")
    ]
    sections.append(
        {
            "key": "knowledge",
            "title": "Knowledge to capture in the exit interview",
            "items": capture,
        }
    )
    return {"employee_id": emp, "generated_at": now, "sections": sections}
