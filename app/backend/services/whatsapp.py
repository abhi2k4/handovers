"""Send WhatsApp messages through the Meta WhatsApp Cloud API.

An interactive message (text plus up to three reply buttons) is sent first. Outside the 24-hour
customer-service window Meta refuses it (error 131047); then an approved one-variable template
(WHATSAPP_TEMPLATE) carries the text instead, without buttons.
"""

from typing import Any

import httpx

from core.config import Settings, get_settings

OUTSIDE_WINDOW = 131047


class SendError(Exception):
    pass


def interactive(phone: str, body: str, buttons: list[dict[str, str]]) -> dict[str, Any]:
    """The request body for a text with reply buttons (titles max 20 chars, max 3)."""
    if not buttons:
        return {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": body},
        }
    return {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body[:1024]},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": b["id"][:256], "title": b["label"][:20]}}
                    for b in buttons[:3]
                ]
            },
        },
    }


def template(phone: str, name: str, body: str) -> dict[str, Any]:
    return {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": name,
            "language": {"code": "en"},
            "components": [{"type": "body", "parameters": [{"type": "text", "text": body[:1024]}]}],
        },
    }


async def send(
    phone: str, body: str, buttons: list[dict[str, str]], s: Settings | None = None
) -> str:
    """Send one message; returns Meta's message id. Raises SendError.

    `s` carries the platform admin's settings (services/delivery.py); `.env` when omitted.
    """
    s = s or get_settings()
    if not s.whatsapp_enabled or s.whatsapp_token is None:
        raise SendError("WhatsApp is not configured")
    url = f"https://graph.facebook.com/{s.whatsapp_api_version}/{s.whatsapp_phone_id}/messages"
    headers = {"Authorization": f"Bearer {s.whatsapp_token.get_secret_value()}"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=interactive(phone, body, buttons), headers=headers)
        error = r.json().get("error", {}) if r.status_code >= 400 else {}
        if error.get("code") == OUTSIDE_WINDOW and s.whatsapp_template:
            r = await client.post(
                url, json=template(phone, s.whatsapp_template, body), headers=headers
            )
            error = r.json().get("error", {}) if r.status_code >= 400 else {}
        if r.status_code >= 400:
            raise SendError(str(error.get("message") or r.text)[:300])
        return str(r.json()["messages"][0]["id"])


def button_reply(payload: dict[str, Any]) -> list[tuple[str, str]]:
    """(phone, button id) for every reply-button tap in a webhook payload."""
    taps = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            for msg in (change.get("value") or {}).get("messages") or []:
                reply = (msg.get("interactive") or {}).get("button_reply") or {}
                if reply.get("id"):
                    taps.append((str(msg.get("from", "")), str(reply["id"])))
    return taps
