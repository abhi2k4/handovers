"""Alert channels the platform admin sets up (WhatsApp, email): values, switch, Test. No network."""

from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from core.config import Settings
from services import delivery, email

ENV = Settings(whatsapp_token=SecretStr("env-token"), whatsapp_phone_id="111")


class ChannelGraph:
    """Just the Channel node: what channel_get reads and channel_set writes."""

    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}

    async def one(self, name: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        assert name == "channel_get"
        return self.rows.get(params["id"]) if params else None

    async def run(self, name: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        assert name == "channel_set"
        row = self.rows.get(params["id"]) or {"config": None, "enabled": None}
        self.rows[params["id"]] = {
            "config": params["config"] if params["config"] is not None else row["config"],
            "enabled": params["enabled"] if params["enabled"] is not None else row["enabled"],
        }
        return []


async def test_env_works_until_the_platform_admin_changes_anything() -> None:
    graph = ChannelGraph()
    assert (await delivery.effective(graph, ENV)).whatsapp_enabled  # type: ignore[arg-type]
    view = await delivery.describe(graph, ENV, "whatsapp")  # type: ignore[arg-type]
    assert view["enabled"] and view["configured"]
    token = next(f for f in view["fields"] if f["key"] == "whatsapp_token")
    assert token["source"] == "server" and "env-token" not in token["value"]  # masked


async def test_the_master_switch_turns_whatsapp_off_for_everyone() -> None:
    graph = ChannelGraph()
    await delivery.set_enabled(graph, "whatsapp", False, "platform:admin")  # type: ignore[arg-type]
    assert not (await delivery.effective(graph, ENV)).whatsapp_enabled  # type: ignore[arg-type]
    await delivery.set_enabled(graph, "whatsapp", True, "platform:admin")  # type: ignore[arg-type]
    assert (await delivery.effective(graph, ENV)).whatsapp_enabled  # type: ignore[arg-type]


async def test_app_values_win_and_a_blank_secret_keeps_the_stored_one() -> None:
    graph = ChannelGraph()
    values = {"whatsapp_phone_id": "222", "whatsapp_token": "app-token"}
    await delivery.save(graph, "whatsapp", values, "platform:admin")  # type: ignore[arg-type]
    await delivery.save(graph, "whatsapp", {"whatsapp_token": ""}, "platform:admin")  # type: ignore[arg-type]
    cfg = await delivery.effective(graph, ENV)  # type: ignore[arg-type]
    assert cfg.whatsapp_phone_id == "222"
    assert cfg.whatsapp_token is not None and cfg.whatsapp_token.get_secret_value() == "app-token"


async def test_test_reads_the_number_from_meta_and_reports_a_refusal() -> None:
    graph = ChannelGraph()

    def meta(request: httpx.Request) -> httpx.Response:
        if request.headers["Authorization"] == "Bearer env-token":
            return httpx.Response(200, json={"display_phone_number": "+91 90000 00000"})
        return httpx.Response(401, json={"error": {"message": "Invalid OAuth access token."}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(meta)) as http:
        ok = await delivery.test(graph, ENV, "whatsapp", http)  # type: ignore[arg-type]
        assert ok["ok"] and "+91 90000 00000" in ok["message"]
        await delivery.save(graph, "whatsapp", {"whatsapp_token": "wrong"}, "platform:admin")  # type: ignore[arg-type]
        bad = await delivery.test(graph, ENV, "whatsapp", http)  # type: ignore[arg-type]
    assert not bad["ok"] and "Invalid OAuth" in bad["message"]


MAIL = ENV.model_copy(update={"smtp_host": "mailpit", "smtp_port": 1025, "smtp_from": "a@h.local"})


async def test_email_test_sends_one_message_and_the_switch_turns_email_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(email, "_send", lambda s, msg: sent.append((s.smtp_host, msg["To"])))
    graph = ChannelGraph()
    ok = await delivery.test(graph, MAIL, "email")  # type: ignore[arg-type]
    assert ok["ok"] and sent == [("mailpit", "a@h.local")]
    assert (await delivery.effective(graph, MAIL)).email_enabled  # type: ignore[arg-type]
    await delivery.set_enabled(graph, "email", False, "platform:admin")  # type: ignore[arg-type]
    cfg = await delivery.effective(graph, MAIL)  # type: ignore[arg-type]
    assert not cfg.email_enabled and cfg.whatsapp_enabled  # one channel off, the other untouched


async def test_email_settings_are_typed_and_an_unknown_channel_is_refused() -> None:
    graph = ChannelGraph()
    await delivery.save(
        graph, "email", {"smtp_host": "smtp.x", "smtp_port": "587", "smtp_from": "b@x"}, "a"
    )  # type: ignore[arg-type]
    cfg = await delivery.effective(graph, ENV)  # type: ignore[arg-type]
    assert cfg.smtp_port == 587 and cfg.email_enabled
    with pytest.raises(delivery.InvalidChannel):
        await delivery.save(graph, "email", {"smtp_port": "abc"}, "a")  # type: ignore[arg-type]
    with pytest.raises(delivery.InvalidChannel):
        await delivery.describe(graph, ENV, "pigeon")  # type: ignore[arg-type]


def test_the_webhook_verify_token_stays_a_plain_string() -> None:
    # The webhook compares it as a string (api/alerts.py), so it must not become a SecretStr.
    cfg = delivery._effective(ENV, "whatsapp", {"whatsapp_verify_token": "v"}, None)
    assert cfg.whatsapp_verify_token == "v"
