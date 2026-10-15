"""The successor's companion: answers from what this person's memory holds, with sources.

Retrieval is anchored at the asker's own edges (KNOWS, RESPONSIBLE_FOR, WORKS_WITH). Before a
transfer the successor simply has nothing to retrieve, so the companion abstains. That is enforced
by the graph, not by a prompt. Full-text search only proposes candidates; a transparent rerank
(shared word stems, matching numbers, why/how intent) decides what is relevant.
"""

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from core.clock import now_ms
from core.graph import Graph
from core.llm import LLM, LLMUnavailable

STOP = set(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "done",
        "for",
        "from",
        "had",
        "has",
        "have",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "me",
        "my",
        "of",
        "on",
        "or",
        "our",
        "should",
        "so",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "to",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "whom",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
        "about",
        "tell",
        "explain",
        "please",
        "know",
        "only",
        "still",
    ]
)


def stem(word: str) -> str:
    w = word.lower()
    for suffix, repl in (("ies", "y"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
        if len(w) > 4 and w.endswith(suffix):
            return w[: -len(suffix)] + repl
    return w


def tokens(text: str) -> list[str]:
    return [
        w
        for w in re.findall(r"[a-z0-9₹]+", (text or "").lower())
        if w not in STOP and (len(w) > 2 or w.isdigit())
    ]


def fulltext_query(question: str) -> str:
    parts: list[str] = []
    for w in tokens(question):
        if w.isdigit():
            continue
        s = stem(w)
        parts.append(w)
        if len(s) >= 4:
            parts.append(s[: max(4, len(s) - 1)] + "*")
    return "|".join(dict.fromkeys(parts)) or "zzzz"


def relevance(question: str, title: str, text: str, kind: str) -> float:
    """Share of the question's meaningful stems found in the item (title counts double)."""
    q = {stem(t) for t in tokens(question)}
    if not q:
        return 0.0
    title_stems = {stem(t) for t in tokens(title)}
    body_stems = title_stems | {stem(t) for t in tokens(text)}
    score = sum(2.0 if s in title_stems else 1.0 if s in body_stems else 0.0 for s in q) / (
        2 * len(q)
    )
    low = question.lower()
    if low.startswith("why") and kind in ("Claim", "Decision"):
        score += 0.1
    if low.split()[:1] in (["what"], ["which"], ["when"]) and kind == "Claim":
        score += 0.1
    if low.startswith("how") and kind == "Procedure":
        score += 0.15
    if ("who" in low.split() or "contact" in low) and kind == "Relationship":
        score += 0.2
    return round(score, 3)


MIN_RELEVANCE = 0.3
PAST_WORDS = {
    "before",
    "previous",
    "previously",
    "used",
    "was",
    "originally",
    "earlier",
    "old",
    "former",
}


# Questions about the memory as a whole: answered from everything the person holds, not a search.
OVERVIEW = re.compile(
    r"(my|whole|entire|all)\s+(memory|knowledge|work)|what('?s| is| do i| does)\s+(in\s+)?(my|i)\s"
    r"|what do i (know|own|do|handle|hold)|summar|overview|everything i|my (responsibilit|accounts|contacts|job|role)"
    r"|who do i work with|what am i (responsible|working)|what should i know"
)
FOLLOW_UP = {"why", "how", "when", "who", "and", "then", "that", "it", "this", "more", "else"}


_IDS = re.compile(
    r"\s*\((?:clm|dec|proc|resp|sth|acc|src)[:\w@.\-]*(?:,\s*(?:clm|dec|proc|resp|sth|acc|src)[:\w@.\-]*)*\)"
)


def clean(answer: str) -> str:
    """Graph ids in brackets are for citations, not for reading."""
    return _IDS.sub("", answer).strip()


def is_overview(question: str) -> bool:
    return bool(OVERVIEW.search(question.lower()))


def is_follow_up(question: str) -> bool:
    """A short question that leans on the previous one ("and why?", "how?")."""
    words = re.findall(r"[a-z']+", question.lower())
    return len(words) <= 4 and (not tokens(question) or words[0] in FOLLOW_UP)


def digest(person: dict[str, Any]) -> list[dict[str, Any]]:
    """Everything a person holds as short, citable items (ids are graph ids). Personal notes are
    left out: they never leave the person, not even to the model."""
    items: list[dict[str, Any]] = []
    for k in person.get("knowledge") or []:
        if k.get("sensitivity") == "personal" or k.get("status") == "superseded":
            continue
        detail = k.get("rationale") or ("; ".join(k.get("steps") or []) or None)
        items.append(
            {
                "id": k["id"],
                "kind": k["kind"],
                "title": k["title"],
                "detail": detail,
                "only_you": not k.get("others"),
                "inherited": k.get("via") == "transfer",
            }
        )
    for r in person.get("responsibilities") or []:
        items.append(
            {
                "id": r["id"],
                "kind": "Responsibility",
                "title": r["title"],
                "detail": r.get("cadence"),
                "only_you": not r.get("co_owners"),
                "inherited": r.get("via") == "transfer",
            }
        )
    for st in person.get("stakeholders") or []:
        items.append(
            {
                "id": st["id"],
                "kind": "Relationship",
                "title": f"{st['name']}, {st.get('org') or ''}".strip(", "),
                "detail": st.get("context"),
                "only_you": not st.get("other_contacts"),
            }
        )
    for a in person.get("accounts") or []:
        items.append(
            {
                "id": a["id"],
                "kind": "Account",
                "title": a["name"],
                "detail": a.get("role"),
                "only_you": a.get("role") in ("admin", "owner") and not a.get("other_admins"),
            }
        )
    return items


def overview_answer(name: str, items: list[dict[str, Any]]) -> str:
    """Deterministic summary of a memory (used when no LLM is configured)."""
    if not items:
        return f"{name}'s memory is empty so far: nothing has been learned from their work or handed over yet."
    by: dict[str, list[str]] = {}
    for i in items:
        by.setdefault(i["kind"], []).append(i["title"])
    label = {
        "Responsibility": "Work",
        "Decision": "Decisions",
        "Procedure": "How-tos",
        "Claim": "Facts",
        "Relationship": "People",
        "Account": "Accounts",
    }
    lines = [
        f"- {label.get(k, k)} ({len(v)}): " + "; ".join(v[:3]) + (" …" if len(v) > 3 else "")
        for k, v in by.items()
    ]
    sole = sum(1 for i in items if i.get("only_you"))
    return (
        f"{name}'s memory holds {len(items)} items, {sole} of them held by no one else.\n"
        + "\n".join(lines)
    )


def suggestions(items: list[dict[str, Any]]) -> list[str]:
    """Questions worth asking this memory, built from what it actually holds."""
    out = ["What's in my memory?"]
    pick = {
        k: next((i for i in items if i["kind"] == k), None)
        for k in ("Decision", "Procedure", "Relationship", "Claim")
    }
    if d := pick["Decision"]:
        t = d["title"]
        if t.startswith("Current: "):
            # The leaver's answer to "sources disagree": ask why that claim is the current one.
            out.append(f"Why is “{t.removeprefix('Current: ')}” current?")
        else:
            out.append(
                f"Why did we {t[0].lower() + t[1:]}?"
                if not t.lower().startswith("why")
                else t + "?"
            )
    if p := pick["Procedure"]:
        t = p["title"]
        out.append(t + "?" if t.lower().startswith("how") else f"How do I {t[0].lower() + t[1:]}?")
    if r := pick["Relationship"]:
        out.append(f"Who is {r['title'].split(',')[0]} and what do I need to know?")
    elif c := pick["Claim"]:
        out.append(f"Is this still true: {c['title']}?")
    if any(i.get("only_you") for i in items):
        out.append("What do only I know?")
    return out[:5]


def compose(top: dict[str, Any]) -> str:
    """Deterministic answer from the best item (used when no LLM is configured)."""
    if top["kind"] == "Relationship":
        return f"{top['title']}. {top.get('rationale') or ''}".strip()
    if top["kind"] == "Responsibility":
        return f"You now own: {top['title']}" + (
            f" ({top['cadence']})." if top.get("cadence") else "."
        )
    parts = [top["title"].rstrip(".") + "."]
    why = top.get("decision_rationale") or top.get("rationale")
    if why:
        parts.append(f"Why: {why}")
    if top.get("previous_value"):
        parts.append(f"Before that it was {top['previous_value']}.")
    if top.get("steps"):
        parts.append("Steps: " + "; ".join(top["steps"]) + ".")
    return " ".join(parts)


async def retrieve(graph: Graph, emp: str, question: str) -> list[dict[str, Any]]:
    """Candidates from the asker's own memory, reranked, with full context."""
    now, q = now_ms(), fulltext_query(question)
    ranked: list[tuple[float, dict[str, Any]]] = []
    past = bool(PAST_WORDS & set(re.findall(r"[a-z]+", question.lower())))
    numbers = set(re.findall(r"\d+", question))
    for h in await graph.read("companion_search", {"emp": emp, "q": q, "now": now, "k": 25}):
        # Notes that resolved a contradiction live on as supersession; they are not answers
        # unless the question asks which value is current.
        if h["id"].startswith("dec:current:") and "current" not in question.lower():
            continue
        score = relevance(
            question, h["title"], f"{h.get('text') or ''} {h.get('value') or ''}", h["kind"]
        )
        superseded = (h.get("valid_to") or 0) <= now
        # Prefer what is true now, unless the question asks about the past.
        score += (0.15 if past else -0.1) if superseded else 0.0
        # A number in the question that equals the item's value ("5 times") is a strong signal.
        if h.get("value") and str(h["value"]).strip("₹ ") in numbers:
            score += 0.2
        ranked.append((round(score, 3), h))
    for h in await graph.read(
        "companion_search_stakeholders", {"emp": emp, "q": q, "now": now, "k": 5}
    ):
        item = {
            "id": h["id"],
            "kind": "Relationship",
            "title": f"{h['name']}, {h.get('org')}",
            "rationale": h.get("context"),
            "via": h.get("via"),
            "from_name": h.get("from_name"),
            "evidence": h.get("evidence") or [],
        }
        ranked.append(
            (relevance(question, item["title"], h.get("context") or "", "Relationship"), item)
        )
    for h in await graph.read(
        "companion_search_responsibilities", {"emp": emp, "q": q, "now": now, "k": 5}
    ):
        item = {
            "id": h["id"],
            "kind": "Responsibility",
            "title": h["title"],
            "cadence": h.get("cadence"),
            "via": h.get("via"),
            "from_name": h.get("from_name"),
            "evidence": h.get("evidence") or [],
        }
        ranked.append((relevance(question, h["title"], "", "Responsibility") - 0.05, item))
    ranked = [(s, h) for s, h in ranked if s >= MIN_RELEVANCE]
    ranked.sort(key=lambda x: x[0], reverse=True)
    top = ranked[:5]
    knowledge_ids = [h["id"] for _, h in top if h["kind"] in ("Claim", "Decision", "Procedure")]
    ctx_by_id: dict[str, dict[str, Any]] = {}
    if knowledge_ids:
        for c in await graph.read("companion_context", {"emp": emp, "ids": knowledge_ids}):
            c["evidence"] = [e for e in (c.get("evidence") or []) if e.get("id")]
            prev = ctx_by_id.get(c["id"])
            # One row per item; if several decisions justify it, keep the one with the fullest reason.
            if prev is None or len(c.get("decision_rationale") or "") > len(
                prev.get("decision_rationale") or ""
            ):
                ctx_by_id[c["id"]] = c
    # A decision that justifies a retrieved claim is shown as that claim's reason, not on its own.
    explained = {c.get("decision_id") for c in ctx_by_id.values() if c.get("decision_id")}
    top = [(s, h) for s, h in top if h["id"] not in explained][:4]
    out = []
    for score, h in top:
        item = ctx_by_id.get(h["id"], h)
        item["relevance"] = score
        item["evidence"] = [e for e in (item.get("evidence") or []) if e.get("id")]
        out.append(item)
    return out


def _latest_source(evidence: list[dict[str, Any]]) -> str:
    """'Daily report, 9 Oct 2026' for the most recent piece of evidence, or '' if none."""
    dated = [e for e in evidence if e.get("at")]
    if not dated:
        return ""
    e = max(dated, key=lambda x: x["at"])
    d = datetime.fromtimestamp(e["at"] / 1000, tz=UTC)
    when = f"{d.day} {d:%b %Y}"  # portable: no %-d on Windows
    # Daily reports are titled by date already; name them by kind instead of repeating it.
    name = (
        "Daily report" if e.get("kind") == "EOD" else (e.get("title") or e.get("kind") or "source")
    )
    return f"{name}, {when}"


def conflict_answer(top: dict[str, Any], others: list[dict[str, Any]]) -> str:
    """Honest answer when live claims the asker holds disagree: show every value and its source."""
    parts = []
    for c in [top, *others]:
        src = _latest_source(c.get("evidence") or [])
        parts.append(f"\u201c{c['title']}\u201d" + (f" ({src})" if src else ""))
    return (
        "Sources disagree: "
        + " vs ".join(parts)
        + ". Neither has replaced the other yet, so treat this as open until it is confirmed "
        "(the exit interview asks which one is current)."
    )


def _citation(c: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": c["id"],
        "kind": c["kind"],
        "title": c["title"],
        "via": c.get("via"),
        "from": c.get("from_name"),
        "approved_by": c.get("approved_by"),
        "approved_at": c.get("approved_at"),
        "decision": c.get("decision"),
        "previous": c.get("previous_value"),
        "valid_from": c.get("valid_from"),
        "evidence": (c.get("evidence") or [])[:4],
    }


ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "citations": {"type": "array", "items": {"type": "string"}},
        "answered": {"type": "boolean"},
    },
    "required": ["answer", "citations", "answered"],
}


async def _history(graph: Graph, session: str) -> list[dict[str, Any]]:
    rows = await graph.read("session_turns", {"session": session, "limit": 4})
    return list(reversed(rows))


def _items_citations(
    items: list[dict[str, Any]], ctx: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Citations for digest items: full provenance for knowledge, the item itself otherwise."""
    out = []
    for i in items:
        c = ctx.get(i["id"]) or {
            "id": i["id"],
            "kind": i["kind"],
            "title": i["title"],
            "evidence": [],
        }
        out.append(
            _citation({**c, "evidence": [e for e in (c.get("evidence") or []) if e.get("id")]})
        )
    return out


MEMORY_SYSTEM = (
    "You are the work-memory assistant inside Handovers. You answer one person's question using ONLY the "
    "items listed from THEIR memory (things they know, work they own, people they work with, accounts they "
    "hold; some were handed over to them by a colleague who left). Never use outside knowledge, never guess. "
    "State a reason only when an item gives one, in its own terms; never add your own explanation or purpose. "
    "Cite the ids of every item you used. If the items do not answer the question, set answered=false and say "
    "in one sentence what is missing. Write plainly: up to four sentences, or a short list with '- ' lines when "
    "listing several things. Say 'you' to the person. Mention when something was inherited or when only they hold it. "
    "Never write item ids or field names (like only_you or inherited) in the answer; name things in plain words. "
    "A short question usually follows up on the PREVIOUS question: answer that follow-up."
)


async def ask(
    graph: Graph, llm: LLM, emp: str, question: str, session: str | None = None
) -> dict[str, Any]:
    from services import analysis

    now = now_ms()
    session = session or f"ses:{emp}"
    history = await _history(graph, session)
    # A short follow-up ("and why?") searches with the question it follows.
    search = question
    if history and is_follow_up(question):
        search = f"{history[-1]['question']} {question}"
    chat = "".join(
        f"Earlier question: {h['question']}\nEarlier answer: {h['answer']}\n" for h in history[-3:]
    )
    person = await analysis.person(graph, emp) or {}
    name = (person.get("name") or "This person").split(" ")[0]
    items = digest(person)
    ids_all = {i["id"] for i in items}
    ctx = [] if is_overview(question) else await retrieve(graph, emp, search)

    missing: list[str] = []

    async def from_memory(overview: bool) -> dict[str, Any] | None:
        """Answer from the whole memory: the model reads every item and must cite them."""
        if not items:
            return None
        listed = items[:80]
        try:
            out = await llm.json(
                MEMORY_SYSTEM,
                f"{chat}Question: {question}\n\nThe person: {person.get('name')}, {person.get('title')}\n"
                f"Items in their memory:\n" + json.dumps(listed, ensure_ascii=False),
                ANSWER_SCHEMA,
            )
        except LLMUnavailable:
            if overview:
                return {
                    "answer": overview_answer(name, items),
                    "used": items[:6],
                    "method": "graph",
                }
            return None
        valid = [c for c in out.get("citations", []) if c in ids_all]
        if not out.get("answered") or not valid:
            # Keep the model's one line on what is missing; it is more useful than a generic reply.
            missing.append(clean(out.get("answer") or ""))
            return None
        return {
            "answer": out["answer"],
            "used": [i for i in items if i["id"] in valid],
            "method": llm.model,
        }

    if is_overview(question):
        got = await from_memory(True) or {
            "answer": overview_answer(name, items),
            "used": items[:6],
            "method": "graph",
        }
        kctx = (
            {
                c["id"]: c
                for c in await graph.read(
                    "companion_context", {"emp": emp, "ids": [i["id"] for i in got["used"]]}
                )
            }
            if got["used"]
            else {}
        )
        result: dict[str, Any] = {
            "status": "answered",
            "answer": got["answer"],
            "citations": _items_citations(got["used"][:8], kctx),
            "ask": [],
            "method": got["method"],
            "scope": "memory",
        }
    elif not ctx:
        found = await from_memory(False)
        if found:
            got = found
            kctx = {
                c["id"]: c
                for c in await graph.read(
                    "companion_context", {"emp": emp, "ids": [i["id"] for i in got["used"]]}
                )
            }
            result = {
                "status": "answered",
                "answer": got["answer"],
                "citations": _items_citations(got["used"][:6], kctx),
                "ask": [],
                "method": got["method"],
                "scope": "memory",
            }
        else:
            cands = await graph.read(
                "knowledge_candidates", {"q": fulltext_query(search), "now": now, "k": 12}
            )
            relevant = [
                c["id"]
                for c in cands
                if relevance(
                    search, c["title"], f"{c.get('text') or ''} {c.get('value') or ''}", c["kind"]
                )
                >= MIN_RELEVANCE
            ]
            who = (
                await graph.read("who_holds", {"ids": relevant[:5], "emp": emp}) if relevant else []
            )
            result = {
                "status": "abstained",
                "answer": next(
                    (m for m in missing if m), "Nothing in your memory covers this yet."
                ),
                "ask": [{"id": w["id"], "name": w["name"], "title": w["title"]} for w in who],
                "citations": [],
                "method": "graph",
            }
    elif ctx[0]["kind"] == "Claim" and (
        conflicts := await graph.read(
            "companion_conflicts", {"emp": emp, "ids": [ctx[0]["id"]], "now": now}
        )
    ):
        # Live claims disagree: answer with both and their sources, no LLM, no silent pick.
        others = [{**c, "evidence": [e for e in c["evidence"] if e.get("id")]} for c in conflicts]
        result = {
            "status": "answered",
            "conflict": True,
            "answer": conflict_answer(ctx[0], others),
            "citations": [_citation(ctx[0]), *(_citation(c) for c in others)],
            "ask": [],
            "method": "graph",
        }
    else:
        ids = [c["id"] for c in ctx]
        answer, cited, method = compose(ctx[0]), [ctx[0]["id"]], "graph"
        try:
            out = await llm.json(
                "You answer a new employee's question using ONLY the items provided from their inherited work "
                "memory. Cite the ids you used. If the items don't answer the question, set answered=false and say "
                "briefly what is missing. At most three sentences. Mention when something used to be different. "
                "State a reason only when an item gives one, in its own terms; never add your own explanation.",
                f"{chat}Question: {question}\n\nItems:\n"
                + json.dumps(
                    [
                        {
                            k: c.get(k)
                            for k in (
                                "id",
                                "kind",
                                "title",
                                "rationale",
                                "value",
                                "steps",
                                "decision",
                                "decision_rationale",
                                "previous_value",
                                "cadence",
                            )
                        }
                        for c in ctx
                    ],
                    ensure_ascii=False,
                ),
                ANSWER_SCHEMA,
            )
            valid = [c for c in out.get("citations", []) if c in ids]
            if out.get("answered") and valid:
                answer, cited, method = clean(out["answer"]), valid, llm.model
            elif not out.get("answered"):
                answer, cited, method = clean(out.get("answer") or "") or answer, [], llm.model
        except LLMUnavailable:
            pass
        used = [c for c in ctx if c["id"] in cited]
        result = {
            "status": "answered" if used else "abstained",
            "answer": answer if used else (answer or "Nothing in your memory covers this yet."),
            "citations": [_citation(c) for c in used],
            "ask": [],
            "method": method,
        }
    await graph.run(
        "session_add_turn",
        {
            "session": session,
            "emp": emp,
            "turn": f"turn:{uuid.uuid4().hex[:10]}",
            "question": question,
            "answer": result["answer"],
            "status": result["status"],
            "now": now,
            "used": [c["id"] for c in result["citations"]],
        },
    )
    return result


async def retrieve_ids(graph: Graph, emp: str, question: str) -> list[str]:
    """Retrieval only (benchmark): ids the companion would use."""
    return [c["id"] for c in await retrieve(graph, emp, question)]
