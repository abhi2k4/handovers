"""Salesforce CRM: contacts and opportunities, via the REST API (SOQL) and an access token."""

from typing import Any

import httpx

from connectors.base import Connector, Field, Pull, secret
from connectors.crm import contact_source, deal_source
from connectors.http import get_json
from core.config import Settings
from ingestion.pipeline import Resolver

SF_VERSION = "v61.0"


class Salesforce(Connector):
    id = "salesforce"
    name = "Salesforce"
    category = "crm"
    fields = (
        Field("salesforce_instance_url", "Instance URL", placeholder="https://your-domain.my.salesforce.com"),
        Field("salesforce_token", "Access token", secret=True, hint="sf org display shows it for a Developer Edition org."),
    )  # fmt: skip

    async def check(self, http: httpx.AsyncClient, s: Settings) -> str:
        base = s.salesforce_instance_url.rstrip("/")
        headers = {"Authorization": f"Bearer {secret(s.salesforce_token)}"}
        await get_json(
            http, f"{base}/services/data/{SF_VERSION}/query", headers=headers,
            params={"q": "SELECT Id FROM Contact LIMIT 1"},
        )  # fmt: skip
        return f"Connected to {httpx.URL(base).host}. Can read contacts."

    async def pull(
        self, http: httpx.AsyncClient, s: Settings, res: Resolver, since: str | None
    ) -> Pull:
        base = s.salesforce_instance_url.rstrip("/")
        headers = {"Authorization": f"Bearer {secret(s.salesforce_token)}"}
        # SOQL datetime literals are unquoted ISO timestamps; the cursor is Salesforce's own value.
        after = f" WHERE LastModifiedDate > {since}" if since else ""
        out = Pull(cursor=since)

        async def query(soql: str) -> list[dict[str, Any]]:
            rows: list[dict[str, Any]] = []
            url: str | None = f"{base}/services/data/{SF_VERSION}/query"
            params: dict[str, str] | None = {"q": soql}
            while url:
                page = await get_json(http, url, headers=headers, params=params)
                rows += page.get("records", [])
                nxt = page.get("nextRecordsUrl")
                url, params = (f"{base}{nxt}", None) if nxt else (None, None)
            return rows

        contacts = await query(
            "SELECT Id, Name, Email, Account.Name, Owner.Email, LastModifiedDate FROM Contact"
            f"{after} ORDER BY LastModifiedDate"
        )
        for c in contacts:
            owner = res.person((c.get("Owner") or {}).get("Email"))
            out.sources.append(
                contact_source("salesforce", c["Id"], c["Name"], c.get("Email"),
                               (c.get("Account") or {}).get("Name"), owner, c["LastModifiedDate"])
            )  # fmt: skip
            out.cursor = max(out.cursor or "", c["LastModifiedDate"])
        deals = await query(
            "SELECT Id, Name, StageName, Amount, Owner.Email, LastModifiedDate FROM Opportunity"
            f"{after} ORDER BY LastModifiedDate"
        )
        for d in deals:
            owner = res.person((d.get("Owner") or {}).get("Email"))
            out.sources.append(
                deal_source("salesforce", d["Id"], d["Name"], d.get("StageName"), d.get("Amount"),
                            owner, d["LastModifiedDate"])
            )  # fmt: skip
            out.cursor = max(out.cursor or "", d["LastModifiedDate"])
        return out
