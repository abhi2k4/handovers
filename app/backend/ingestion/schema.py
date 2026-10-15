"""The closed ontology. Seed fixtures and live LLM extraction both produce these models.

A `SourceIn` is one immutable piece of evidence (an EOD report, a PR, a message, an uploaded file
chunk). Its `facts` are what that evidence says about someone's work. The writer turns them into
graph nodes and edges with fixed Cypher; nothing outside these kinds reaches the graph.
"""

from typing import Literal

from pydantic import BaseModel, Field

FactKind = Literal[
    "responsibility", "decision", "procedure", "claim", "access", "stakeholder", "skill"
]
Cadence = Literal["daily", "weekly", "biweekly", "monthly", "quarterly", "adhoc"]
SourceKind = Literal[
    "EOD",
    "Message",
    "Ticket",
    "PullRequest",
    "Commit",
    "Meeting",
    "Document",
    "Upload",
    "CRMNote",
    "InterviewAnswer",
]
Sensitivity = Literal["internal", "restricted", "personal"]
SkillCategory = Literal["tool", "skill", "domain"]
AccessRole = Literal["admin", "owner", "editor", "member"]
StakeholderKind = Literal["vendor", "client", "agency", "partner"]

# Evidence quality prior per source kind (feeds noisy-OR confidence).
SOURCE_QUALITY: dict[str, float] = {
    "Document": 0.85,
    "InterviewAnswer": 0.85,
    "PullRequest": 0.8,
    "Commit": 0.7,
    "Ticket": 0.65,
    "Meeting": 0.6,
    "EOD": 0.6,
    "CRMNote": 0.6,
    "Upload": 0.6,
    "Message": 0.5,
}


class Fact(BaseModel):
    kind: FactKind
    key: str = Field(description="Stable canonical id, e.g. 'resp:meta-ads-weekly-review'")
    title: str
    area: str | None = Field(
        default=None, description="Area id the fact is about, e.g. 'area:paid-social'"
    )
    skills: list[str] = Field(
        default_factory=list, description="Skill ids this work needs or shows"
    )
    people: list[str] = Field(
        default_factory=list, description="Employee ids; empty = source author"
    )
    quote: str | None = None
    confidence: float = 0.8
    # responsibility
    cadence: Cadence | None = None
    # decision
    rationale: str | None = None
    alternatives: list[str] = Field(default_factory=list)
    # procedure
    steps: list[str] = Field(default_factory=list)
    handles: str | None = None
    # claim
    subject: str | None = None
    predicate: str | None = None
    value: str | None = None
    supersedes: str | None = None
    justified_by: str | None = None
    # access
    system: str | None = None
    role: AccessRole | None = None
    # stakeholder
    org: str | None = None
    stakeholder_kind: StakeholderKind | None = None
    context: str | None = None
    # skill
    category: SkillCategory | None = None


class SourceIn(BaseModel):
    id: str
    kind: SourceKind
    system: str = "upload"
    title: str
    text: str
    occurred_at: str
    author: str | None = None
    attendees: list[str] = Field(default_factory=list)
    sensitivity: Sensitivity = "internal"
    areas: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    url: str | None = None
    status: str | None = None  # tickets: open/closed
    doc_type: str | None = None  # documents: jd/runbook/adr/deck/sop/wiki/notes
    describes_role: str | None = None  # documents with doc_type=jd
    facts: list[Fact] = Field(default_factory=list)


class Employee(BaseModel):
    id: str
    name: str
    email: str
    title: str
    team: str
    role: str
    manager: str | None = None
    status: Literal["active", "incoming", "departed"] = "active"
    joined_at: str


class Org(BaseModel):
    company: str
    teams: list[dict[str, str]]
    roles: list[dict[str, str]]
    employees: list[Employee]
    areas: list[dict[str, str]]
    skills: list[dict[str, str | list[str]]]
