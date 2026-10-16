"""HubSpot CRM: contacts (who owns which customer) and deals, via a private app token."""

from typing import Any

import httpx

from connectors.base import Connector, Field, Pull, secret
from connectors.crm import contact_source, deal_source
from connectors.http import get_json, post_json
from core.config import Settings
from ingestion.pipeline import Resolver

HUBSPOT = "https://api.hubapi.com"


class HubSpot(Connector):
    id = "hubspot"
    name = "HubSpot"
    category = "crm"
    fields = (
        Field("hubspot_token", "Private app token", secret=True, placeholder="pat-...",
              hint="Scopes: contacts, deals and owners (read)."),
    )  # fmt: skip

    async def check(self, http: httpx.AsyncClient, s: Settings) -> str:
        headers = {"Authorization": f"Bearer {secret(s.hubspot_token)}"}
        await get_json(http, f"{HUBSPOT}/crm/v3/owners", headers=headers, params={"limit": 1})
        await get_json(
            http, f"{HUBSPOT}/crm/v3/objects/contacts", headers=headers, params={"limit": 1}
        )
        return "Connected. Can read owners and contacts."

    async def pull(
        self, http: httpx.AsyncClient, s: Settings, res: Resolver, since: str | None
    ) -> Pull:
        headers = {"Authorization": f"Bearer {secret(s.hubspot_token)}"}
        owners_page = await get_json(
            http, f"{HUBSPOT}/crm/v3/owners", headers=headers, params={"limit": 100}
        )
        owners = {str(o["id"]): res.person(o.get("email")) for o in owners_page.get("results", [])}
        out = Pull(cursor=since)

        async def search(kind: str, props: list[str]) -> list[dict[str, Any]]:
            body: dict[str, Any] = {
                "properties": props,
                "sorts": [{"propertyName": "hs_lastmodifieddate", "direction": "ASCENDING"}],
                "limit": 100,
            }
            if since:
                body["filterGroups"] = [
                    {
                        "filters": [
                            {
                                "propertyName": "hs_lastmodifieddate",
                                "operator": "GT",
                                "value": since,
                            }
                        ]
                    }
                ]
            data = await post_json(
                http, f"{HUBSPOT}/crm/v3/objects/{kind}/search", headers=headers, json=body
            )
            return list(data.get("results", []))

        for c in await search(
            "contacts", ["firstname", "lastname", "email", "company", "hubspot_owner_id"]
        ):
            p = c["properties"]
            name = " ".join(x for x in (p.get("firstname"), p.get("lastname")) if x) or (
                p.get("email") or "Contact"
            )
            out.sources.append(
                contact_source("hubspot", c["id"], name, p.get("email"), p.get("company"),
                               owners.get(str(p.get("hubspot_owner_id"))), c["updatedAt"])
            )  # fmt: skip
            out.cursor = max(out.cursor or "", c["updatedAt"])
        for d in await search("deals", ["dealname", "dealstage", "amount", "hubspot_owner_id"]):
            p = d["properties"]
            out.sources.append(
                deal_source("hubspot", d["id"], p.get("dealname") or "Deal", p.get("dealstage"),
                            p.get("amount"), owners.get(str(p.get("hubspot_owner_id"))), d["updatedAt"])
            )  # fmt: skip
            out.cursor = max(out.cursor or "", d["updatedAt"])
        return out
