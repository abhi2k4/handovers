"""Slack: channel conversations, one source per thread (or per substantial standalone message).

Uses the Web API with a bot token from the company's own Slack app (scopes: channels:history,
users:read, users:read.email; the bot is invited to each channel). Authors are matched by email.
"""

from datetime import UTC, datetime
from typing import Any

import httpx

from connectors.base import Connector, ConnectorError, Field, Pull, csv_list, secret
from connectors.http import get_json
from core.config import Settings
from ingestion.pipeline import Resolver
from ingestion.schema import SourceIn

API = "https://slack.com/api"
MIN_CHARS = 40  # skip "ok", "thanks" and the like unless they start a thread


async def _call(http: httpx.AsyncClient, s: Settings, method: str, **params: Any) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {secret(s.slack_bot_token)}"}
    data: dict[str, Any] = await get_json(http, f"{API}/{method}", headers=headers, params=params)
    if not data.get("ok"):
        # Slack answers 200 with ok=false; its error code is safe to show (no secrets).
        raise ConnectorError(f"Slack {method}: {data.get('error', 'failed')}")
    return data


class Slack(Connector):
    id = "slack"
    name = "Slack"
    category = "chat"
    fields = (
        Field("slack_bot_token", "Bot token", secret=True, placeholder="xoxb-...",
              hint="From your Slack app: OAuth & Permissions."),
        Field("slack_channels", "Channel IDs", placeholder="C0123ABCD, C0456EFGH",
              hint="Invite the app to each channel first (/invite)."),
    )  # fmt: skip

    async def check(self, http: httpx.AsyncClient, s: Settings) -> str:
        me = await _call(http, s, "auth.test")
        channels = csv_list(s.slack_channels)
        for channel in channels:
            # Fails with "not_in_channel" until the app is invited to it.
            await _call(http, s, "conversations.history", channel=channel, limit=1)
        return f"Connected to {me.get('team')} as {me.get('user')}. Can read {len(channels)} channel(s)."

    async def pull(
        self, http: httpx.AsyncClient, s: Settings, res: Resolver, since: str | None
    ) -> Pull:
        async def call(method: str, **params: Any) -> dict[str, Any]:
            return await _call(http, s, method, **params)

        people: dict[str, str | None] = {}

        async def who(user: str | None) -> str | None:
            if not user:
                return None
            if user not in people:
                profile = (await call("users.info", user=user))["user"].get("profile", {})
                people[user] = res.person(profile.get("email")) or res.person(
                    profile.get("real_name")
                )
            return people[user]

        out = Pull(cursor=since)
        for channel in csv_list(s.slack_channels):
            history = await call(
                "conversations.history", channel=channel, oldest=since or "0", limit=200
            )
            for m in history.get("messages", []):
                if m.get("subtype"):  # joins, bot notices, edits
                    continue
                text = m.get("text") or ""
                replies: list[dict[str, Any]] = []
                if m.get("reply_count"):
                    thread = await call("conversations.replies", channel=channel, ts=m["ts"])
                    replies = thread.get("messages", [])[1:]
                if not replies and len(text) < MIN_CHARS:
                    continue
                author = await who(m.get("user"))
                repliers = {await who(r.get("user")) for r in replies}
                body = "\n".join([text, *(r.get("text") or "" for r in replies)]).strip()
                out.sources.append(
                    SourceIn(
                        id=f"src:slack:{channel}-{m['ts'].replace('.', '-')}",
                        kind="Message",
                        system="slack",
                        title=text.split("\n")[0][:90] or "Slack thread",
                        text=body,
                        occurred_at=datetime.fromtimestamp(float(m["ts"]), tz=UTC).isoformat(),
                        author=author,
                        attendees=sorted(p for p in repliers if p and p != author),
                    )
                )
                out.cursor = max(out.cursor or "0", m["ts"], key=float)
        return out
