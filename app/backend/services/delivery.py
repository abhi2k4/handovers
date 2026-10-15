"""How alerts leave the app: the WhatsApp and email channels, set up by the platform admin.

The platform admin enters each channel's settings once (Integrations → Alerts); they are stored
encrypted on a `Channel` node, with `.env` (`WHATSAPP_*`, `SMTP_*`) as the fallback, the same way
connector credentials work. Each channel has a **master switch**: off, nobody gets that channel and
every alert still shows in the app; it defaults to on, so a deployment set up through `.env` keeps
working. Each person still chooses their own number, email and alert types (services/alerts.py).
"""

import json
from typing import Any

import httpx
from pydantic import SecretStr

from core import security
from core.clock import now_ms
from core.config import Settings
from core.graph import Graph
from services import email

WHATSAPP = "whatsapp"
EMAIL = "email"

#: Per channel: (settings key, label, masked in the form, placeholder, hint).
FIELDS: dict[str, tuple[tuple[str, str, bool, str, str], ...]] = {
    WHATSAPP: (
        ("whatsapp_phone_id", "Phone number ID", False, "123456789012345",
         "Meta developer app → WhatsApp → API Setup."),
        ("whatsapp_token", "Access token", True, "EAAG...",
         "A system-user token with whatsapp_business_messaging."),
        ("whatsapp_template", "Template (optional)", False, "handovers_alert",
         "An approved one-variable template, used outside the 24-hour window."),
        ("whatsapp_verify_token", "Webhook verify token", True, "any long random string",
         "The same string you enter when registering the webhook in Meta."),
    ),
    EMAIL: (
        ("smtp_host", "SMTP server", False, "smtp.example.com",
         "Empty in Docker: the bundled Mailpit inbox (http://localhost:8025)."),
        ("smtp_port", "Port", False, "587", "587 uses STARTTLS, 465 TLS; Mailpit is 1025."),
        ("smtp_user", "Username (optional)", False, "alerts@example.com", ""),
        ("smtp_password", "Password (optional)", True, "", "An app password, not a personal one."),
        ("smtp_from", "From address", False, "alerts@example.com", "What people see alerts come from."),
    ),
}  # fmt: skip
#: What switching a channel off clears, so its `*_enabled` answers False.
OFF: dict[str, dict[str, Any]] = {WHATSAPP: {"whatsapp_token": None}, EMAIL: {"smtp_host": ""}}


class InvalidChannel(Exception):
    """The message is shown to the platform admin."""


def _fields(channel: str) -> tuple[tuple[str, str, bool, str, str], ...]:
    if channel not in FIELDS:
        raise InvalidChannel(f"Unknown channel {channel!r}")
    return FIELDS[channel]


async def _row(graph: Graph, channel: str) -> tuple[dict[str, str], bool | None]:
    row = await graph.one("channel_get", {"id": channel})
    if not row:
        return {}, None
    stored: dict[str, str] = {}
    if row.get("config"):
        try:
            stored = json.loads(security.decrypt(row["config"]))
        except security.InvalidToken:
            stored = {}  # APP_SECRET_KEY changed: enter the values again
    return stored, row.get("enabled")


def _typed(key: str, value: str) -> Any:
    """A stored string as the Settings field's own type."""
    current = Settings.model_fields[key].annotation
    if current is int:
        return int(value)
    return SecretStr(value) if "SecretStr" in str(current) else value


def _effective(s: Settings, channel: str, stored: dict[str, str], enabled: bool | None) -> Settings:
    update: dict[str, Any] = {k: _typed(k, v) for k, v in stored.items() if v}
    if enabled is False:
        update |= OFF[channel]  # the master switch: nobody gets this channel
    return s.model_copy(update=update) if update else s


async def effective(graph: Graph, s: Settings) -> Settings:
    """Settings with every channel's app values and switch applied.

    `.whatsapp_enabled` and `.email_enabled` are the answers.
    """
    for channel in FIELDS:
        stored, enabled = await _row(graph, channel)
        s = _effective(s, channel, stored, enabled)
    return s


async def describe(graph: Graph, s: Settings, channel: str) -> dict[str, Any]:
    """One channel for the Alerts tab: the switch, the form (secrets masked), how to finish setup."""
    stored, enabled = await _row(graph, channel)
    fields = []
    for key, label, secret, placeholder, hint in _fields(channel):
        from_env = getattr(s, key, None)
        env_value = (
            from_env.get_secret_value() if isinstance(from_env, SecretStr) else str(from_env or "")
        )
        value = stored.get(key) or env_value
        fields.append({
            "key": key, "label": label, "secret": secret, "placeholder": placeholder, "hint": hint,
            "set": bool(value),
            "value": security.mask(value) if secret and value else ("" if secret else value),
            "source": "app" if stored.get(key) else ("server" if env_value else None),
        })  # fmt: skip
    cfg = _effective(s, channel, stored, None)
    return {
        "channel": channel,
        "enabled": enabled is not False,
        "configured": cfg.whatsapp_enabled if channel == WHATSAPP else cfg.email_enabled,
        "fields": fields,
        "webhook_url": f"{s.app_public_url.rstrip('/')}/api/whatsapp/webhook"
        if channel == WHATSAPP
        else None,
    }


async def save(graph: Graph, channel: str, values: dict[str, str], by: str) -> None:
    """Store the form. A blank secret keeps the stored one."""
    fields = _fields(channel)
    unknown = set(values) - {key for key, *_ in fields}
    if unknown:
        raise InvalidChannel(f"Unknown settings: {', '.join(sorted(unknown))}")
    if values.get("smtp_port", "").strip() and not values["smtp_port"].strip().isdigit():
        raise InvalidChannel("The port is a number, e.g. 587.")
    secret = {key for key, _, masked, _, _ in fields if masked}
    stored, _ = await _row(graph, channel)
    for key, value in values.items():
        if key in secret and not value.strip():
            continue
        stored[key] = value.strip()
    await graph.run(
        "channel_set",
        {"id": channel, "config": security.encrypt(json.dumps(stored)), "enabled": None,
         "by": by, "now": now_ms()},
    )  # fmt: skip


async def set_enabled(graph: Graph, channel: str, on: bool, by: str) -> None:
    _fields(channel)
    await graph.run(
        "channel_set", {"id": channel, "config": None, "enabled": on, "by": by, "now": now_ms()}
    )


async def test(
    graph: Graph, s: Settings, channel: str, http: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    """WhatsApp: read the phone number from Meta (sends nothing). Email: send one to the From address."""
    _fields(channel)
    stored, _ = await _row(graph, channel)
    cfg = _effective(s, channel, stored, None)
    if channel == EMAIL:
        if not cfg.email_enabled:
            return {"ok": False, "message": "Enter the SMTP server and From address first."}
        try:
            await email.send(
                cfg, cfg.smtp_from, "Handovers test email", "Email alerts are set up correctly."
            )
        except email.SendError as exc:
            return {"ok": False, "message": str(exc)}
        return {"ok": True, "message": f"Sent a test email to {cfg.smtp_from}."}
    if not cfg.whatsapp_enabled or cfg.whatsapp_token is None:
        return {"ok": False, "message": "Enter the phone number ID and access token first."}
    url = f"https://graph.facebook.com/{cfg.whatsapp_api_version}/{cfg.whatsapp_phone_id}"
    headers = {"Authorization": f"Bearer {cfg.whatsapp_token.get_secret_value()}"}
    client = http or httpx.AsyncClient(timeout=10)
    try:
        r = await client.get(url, headers=headers, params={"fields": "display_phone_number"})
    except httpx.HTTPError:
        return {"ok": False, "message": "Could not reach graph.facebook.com"}
    finally:
        if http is None:
            await client.aclose()
    if r.status_code >= 400:
        reason = (r.json().get("error") or {}).get("message", "") if r.content else ""
        return {"ok": False, "message": f"Meta refused it ({r.status_code}). {reason}"[:300]}
    number = r.json().get("display_phone_number") or cfg.whatsapp_phone_id
    return {"ok": True, "message": f"Connected. Alerts are sent from {number}."}
