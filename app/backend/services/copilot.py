"""In-app copilot: one search bar on every page, answering from two grounded sources only.

1. The app guide below (what Handovers is, what each page shows and allows), for questions about
   the product or the current page.
2. The asker's own memory in the graph, through the companion (citations, abstains when nothing
   matches), for questions about work.

The LLM only words answers from these sources; without an LLM the guide answers from templates.
"""

from typing import Any

from core.graph import Graph
from core.llm import LLM, LLMUnavailable
from services import companion
from services.access import Caller

APP = (
    "Handovers keeps a memory of everyone's work in a FalkorDB graph, learned from tickets, pull "
    "requests, daily reports, messages and documents. When someone resigns, HR gets a job "
    "description written from their real work, a screening kit, an interview kit and a handover "
    "plan ordered by what breaks first. The leaver answers only the questions nothing else explains "
    "and confirms each answer. Their manager approves what moves to the successor, who then asks a "
    "companion that answers from the inherited memory with sources and says when it does not know. "
    "Rules: HR runs the process but cannot read answers or approve; only the manager approves; "
    "items marked private never move. 'View as' (bottom of the sidebar) switches between demo people."
)

PAGES: dict[str, dict[str, Any]] = {
    "home": {
        "title": "Home",
        "about": "Your own dashboard. What it shows depends on who you are: HR sees the organisation "
        "overview, leadership a read-only view of risk, handovers and outcomes, managers their team and approvals, a leaver their handover checklist, "
        "a successor what they inherited, everyone else what only they hold.",
        "can": ["See your KPIs at a glance", "Jump to the next thing that needs you"],
    },
    "insights": {
        "title": "Insights",
        "about": "Organisation KPIs for HR and leadership: the north star (share of single-person "
        "knowledge resolved before each last day), handover progress, key-person risk, knowledge "
        "health, backup coverage by team, and outcomes of completed handovers.",
        "can": [
            "Spot teams with little backup",
            "See who holds the most on their own",
            "Track handovers in progress",
        ],
    },
    "people": {
        "title": "People",
        "about": "Everyone and how much they hold alone (work, accounts, contacts, knowledge). Managers "
        "see their team only.",
        "can": ["Open a person's memory", "Simulate what would be left with no one if they left"],
    },
    "person": {
        "title": "Person memory",
        "about": "What the system has learned about one person's work: responsibilities, accounts, "
        "contacts, knowledge and the sources behind each. HR sees this without knowledge content.",
        "can": ["Mark your own items private", "See which items only this person holds"],
    },
    "handovers": {
        "title": "Handovers",
        "about": "Open handovers with days left and what is still open.",
        "can": [
            "Start a handover",
            "Open one to see its plan, hiring kit, exit interview and transfer",
        ],
    },
    "handover": {
        "title": "Handover workspace",
        "about": "One person's handover: the plan ordered by what breaks first, the job description "
        "(with what the old one missed), screening kit, interview kit, exit interview and transfer. "
        "HR sees interview progress, not answers; only the manager can approve the transfer.",
        "can": [
            "Generate the job description and kits",
            "Check a resume against the criteria",
            "Review and approve the transfer (manager)",
        ],
    },
    "ask": {
        "title": "Ask",
        "about": "The companion: answers only from what your memory holds, cites the source and who "
        "approved inherited items, and says it does not know instead of guessing.",
        "can": ["Ask why something is set the way it is", "Ask how a recurring task is done"],
    },
    "accounts": {
        "title": "Accounts to reassign",
        "about": "Accounts where someone who is leaving is the only admin. IT reassigns them before the last day.",
        "can": ["See which accounts are at risk and by when"],
    },
    "sources": {
        "title": "Sources",
        "about": "Where the memory comes from: uploads and connector records, plus a review queue for "
        "low-confidence facts that are not saved until a person adds them.",
        "can": ["Upload a document", "Review extracted facts"],
    },
}

APP_WORDS = (
    "this page",
    "this screen",
    "what can i",
    "how do i",
    "how does",
    "what is handovers",
    "what does this",
    "where do i",
    "where can i",
    "help",
    "what is this",
    "how to use",
)


def is_app_question(question: str) -> bool:
    q = question.lower()
    return any(w in q for w in APP_WORDS)


def _guide_template(page: dict[str, Any]) -> str:
    can = "; ".join(page["can"])
    return f"{page['title']}: {page['about']} Here you can: {can}."


async def _guide_answer(llm: LLM, page: dict[str, Any], question: str) -> tuple[str, str]:
    if not llm.enabled:
        return _guide_template(page), "template"
    system = (
        "You are the in-app guide for Handovers. Answer in at most 4 short sentences using ONLY the "
        "context. If the context does not cover the question, say you can answer questions about "
        "this app and about the user's own work memory. No markdown headings."
    )
    prompt = (
        f"App: {APP}\n\nCurrent page: {page['title']}. {page['about']} "
        f"Actions: {'; '.join(page['can'])}.\n\nQuestion: {question}"
    )
    try:
        return await llm.text(system, prompt), llm.model
    except LLMUnavailable:
        return _guide_template(page), "template"


async def ask(
    graph: Graph, llm: LLM, caller: Caller | None, question: str, page_key: str
) -> dict[str, Any]:
    page = PAGES.get(page_key, PAGES["home"])
    if caller is not None and not is_app_question(question):
        # Work questions are answered from the caller's memory only, including an honest
        # "not recorded" or "ask X" when the memory does not cover it.
        memory = await companion.ask(graph, llm, caller.id, question)
        return {"source": "memory", **memory}
    answer, method = await _guide_answer(llm, page, question)
    note = None if caller else "Choose a person in View as to ask about their work."
    return {
        "source": "guide",
        "status": "answered",
        "answer": answer,
        "method": method,
        "citations": [],
        "ask": [],
        "note": note,
    }


def suggestions(page_key: str) -> list[str]:
    page = PAGES.get(page_key, PAGES["home"])
    return [f"What is the {page['title']} page?", "What can I do here?", "What is Handovers?"]
