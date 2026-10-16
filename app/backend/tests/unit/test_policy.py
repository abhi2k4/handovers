from core.clock import DAY_MS
from services import policy
from services.companion import fulltext_query, relevance, stem
from services.generators import check_resume_rules


def test_dedupe_keeps_highest_priority_rule_per_target() -> None:
    seeds = [
        policy.GapSeed("G2", "dec:x", "Knowledge", "X", "q", policy.priority("G2")),
        policy.GapSeed("G1", "dec:x", "Decision", "X", "q", policy.priority("G1")),
        policy.GapSeed("G7A", "acc:y", "Account", "Y", "q", policy.priority("G7A")),
    ]
    out = policy.dedupe_gaps(seeds)
    assert [(s.rule, s.target) for s in out] == [("G7A", "acc:y"), ("G1", "dec:x")]


def test_seed_question_mentions_previous_value() -> None:
    q = policy.seed_question(
        "G1", {"title": "Retries are 3", "predicate": "retry_limit", "previous": "5"}
    )
    assert "change from 5" in q


def test_next_due_and_overdue() -> None:
    now = 100 * DAY_MS
    due, overdue = policy.next_due(now - 40 * DAY_MS, "monthly", now)
    assert due == now - 9 * DAY_MS and overdue
    assert policy.next_due(None, "weekly", now) == (None, False)


def test_transfer_excludes_personal_private_and_known() -> None:
    assert policy.transfer_decision({"sensitivity": "personal", "confidence": 0.9}) == (
        False,
        "personal",
    )
    assert policy.transfer_decision({"private": True, "confidence": 0.9}) == (False, "kept private")
    assert policy.transfer_decision({"already_held": True, "confidence": 0.9}) == (
        False,
        "already known",
    )
    assert policy.transfer_decision({"confidence": 0.2}) == (False, "low confidence")
    assert policy.transfer_decision({"confidence": 0.8, "current": False}) == (True, "history")


def test_resume_rules_quote_evidence_and_never_score() -> None:
    criteria = [
        {"id": "skill:python", "label": "Hands-on Python", "level": "must", "signals": ["python"]},
        {
            "id": "resp:x",
            "label": "Has done: run migrations",
            "level": "must",
            "signals": ["alembic"],
        },
        {"id": "skill:figma", "label": "Figma", "level": "nice", "signals": ["figma"]},
    ]
    out = check_resume_rules("Five years of Python and FastAPI.", criteria)
    verdicts = {v["id"]: v["verdict"] for v in out}
    assert verdicts == {"skill:python": "meets", "resp:x": "unclear", "skill:figma": "missing"}
    assert "Python" in (out[0]["quote"] or "")
    assert all("score" not in v for v in out)


def test_retrieval_ranking_prefers_matching_title() -> None:
    q = "Why does the reconciliation service retry only 3 times?"
    assert stem("retries") == stem("retry")
    claim = relevance(q, "Reconciliation service retries settlement calls 3 times", "", "Claim")
    deploy = relevance(q, "Deploy the reconciliation service", "merge to main", "Procedure")
    assert claim > deploy
    assert "retr*" in fulltext_query(q)


def test_a_resignation_reaches_hr_and_the_leavers_manager_once_each() -> None:
    from services.alerts import resignation_recipients

    assert resignation_recipients(["emp:meera"], "emp:aditi", None) == [
        ("emp:meera", False),
        ("emp:aditi", True),
    ]
    # The person who started it already knows; a manager who is also HR hears once, as manager.
    assert resignation_recipients(["emp:meera"], "emp:aditi", "emp:meera") == [("emp:aditi", True)]
    assert resignation_recipients(["emp:meera"], "emp:meera", None) == [("emp:meera", True)]
    assert resignation_recipients(["emp:meera"], None, None) == [("emp:meera", False)]
