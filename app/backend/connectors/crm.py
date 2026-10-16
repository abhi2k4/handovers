"""What every CRM connector produces: contacts as stakeholder facts, deals as CRM notes.

Each contact becomes a stakeholder fact on its owner: exactly the "only Nisha talks to this customer"
risk the gap rules look for. Deals become short CRM notes for extraction. Owners are matched to
employees by email.
"""

import re
from typing import Any

from ingestion.schema import Fact, SourceIn


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]


def contact_source(
    system: str, cid: str, name: str, email: str | None, company: str | None, owner: str | None,
    at: str,
) -> SourceIn:  # fmt: skip
    org = company or "Unknown company"
    return SourceIn(
        id=f"src:{system}:contact-{cid}",
        kind="CRMNote",
        system=system,
        title=f"{name} ({org})",
        text=f"CRM contact {name}, {org}" + (f", {email}" if email else ""),
        occurred_at=at,
        author=owner,
        facts=[
            Fact(
                kind="stakeholder",
                key=f"sth:{_slug(email or f'{name}-{org}')}",
                title=name,
                org=org,
                stakeholder_kind="client",
                people=[owner] if owner else [],
                confidence=0.9,  # the CRM's own owner field, not an inference
            )
        ],
    )


def deal_source(
    system: str, did: str, name: str, stage: str | None, amount: Any, owner: str | None, at: str
) -> SourceIn:
    detail = ", ".join(
        x for x in (f"stage {stage}" if stage else "", f"amount {amount}" if amount else "") if x
    )
    return SourceIn(
        id=f"src:{system}:deal-{did}",
        kind="CRMNote",
        system=system,
        title=f"Deal: {name}",
        text=f"Deal {name}" + (f" ({detail})" if detail else "") + ". Owner manages this deal.",
        occurred_at=at,
        author=owner,
    )
