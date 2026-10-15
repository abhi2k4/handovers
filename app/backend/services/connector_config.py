"""Connector settings entered in the app: stored encrypted in the graph, never returned in full.

The effective settings for a connector are the server's environment settings with the app's
values on top. A blank secret on save keeps the stored one, so an admin can change a channel list
without retyping a token.

A work tool can be connected more than once (a product GitHub and a client one, a sales Jira and
an engineering one): each **account** has its own settings, sync state and the teams it serves. The
first account's id is the platform id (`github`), so a platform connected once looks exactly as
before; more are `github:<slug>`. Server environment values apply to the first account only.

Some categories allow one active connector at a time (`EXCLUSIVE`: the directory, which decides
who works here). Activating one makes the others in its category inactive in the same write; their
settings are kept, so switching back needs no re-entry. Only the active one syncs.
"""

import json
import re
from typing import Any

from pydantic import SecretStr

from connectors import REGISTRY
from connectors.base import Connector
from core import security
from core.clock import now_ms
from core.config import Settings
from core.graph import Graph


class InvalidConfig(Exception):
    pass


#: Categories where only one connector may be active at a time.
EXCLUSIVE = frozenset({"directory"})


def exclusive(c: Connector) -> bool:
    return c.category in EXCLUSIVE


async def active_in(graph: Graph, category: str) -> str | None:
    """The id of the active connector in `category`, if any."""
    ids = {c.id for c in REGISTRY.values() if c.category == category}
    rows = await graph.read("connector_list", {})
    return next((r["id"] for r in rows if r["id"] in ids and r.get("active")), None)


async def activate(graph: Graph, c: Connector) -> None:
    """Make `c` the active connector of its category; every other one there becomes inactive."""
    if not exclusive(c):
        raise InvalidConfig(f"{c.name} does not have one-active-at-a-time")
    ids = [x.id for x in REGISTRY.values() if x.category == c.category]
    await graph.run("connector_activate", {"id": c.id, "ids": ids, "now": now_ms()})


async def deactivate(graph: Graph, c: Connector) -> None:
    await graph.run("connector_deactivate", {"id": c.id})


async def record_test(graph: Graph, cid: str, ok: bool, message: str) -> None:
    """Keep the result of testing the saved settings, for the card."""
    await graph.run("connector_tested", {"id": cid, "ok": ok, "message": message, "now": now_ms()})


async def load(graph: Graph, cid: str) -> dict[str, str]:
    row = await graph.one("connector_config_get", {"id": cid})
    if not row or not row.get("config"):
        return {}
    try:
        data: dict[str, str] = json.loads(security.decrypt(row["config"]))
    except security.InvalidToken:
        return {}  # APP_SECRET_KEY changed: the stored values are unreadable, re-enter them
    return data


def platform_of(account: str) -> str:
    """`github:product` -> `github`; a first account's id is the platform id itself."""
    return account.split(":", 1)[0]


def _base(s: Settings, c: Connector, account: str) -> Settings:
    """What an account starts from: the server's values for the first account, nothing for more."""
    if account == c.id:
        return s
    return s.model_copy(update=dict.fromkeys(c.needs))


def effective(
    s: Settings, c: Connector, stored: dict[str, str], account: str | None = None
) -> Settings:
    secret_keys = {f.key for f in c.fields if f.secret}
    update: dict[str, Any] = {
        k: SecretStr(v) if k in secret_keys else v for k, v in stored.items() if k in c.needs and v
    }
    base = _base(s, c, account or c.id)
    return base.model_copy(update=update) if update else base


async def settings_for(
    graph: Graph, s: Settings, c: Connector, account: str | None = None
) -> Settings:
    return effective(s, c, await load(graph, account or c.id), account)


async def _merged(
    graph: Graph, c: Connector, values: dict[str, str], account: str | None = None
) -> dict[str, str]:
    """The stored values with the form's on top; a blank secret keeps the stored one."""
    unknown = set(values) - set(c.needs)
    if unknown:
        raise InvalidConfig(f"Unknown settings: {', '.join(sorted(unknown))}")
    stored = await load(graph, account or c.id)
    secret_keys = {f.key for f in c.fields if f.secret}
    for key, value in values.items():
        value = value.strip()
        if key in secret_keys and not value:
            continue
        stored[key] = value
    return stored


async def preview(
    graph: Graph, s: Settings, c: Connector, values: dict[str, str], account: str | None = None
) -> Settings:
    """Settings as they would be with the form's values, without saving them (Test connection)."""
    return effective(s, c, await _merged(graph, c, values, account), account)


async def save(
    graph: Graph,
    c: Connector,
    values: dict[str, str],
    by: str,
    account: str | None = None,
    label: str | None = None,
) -> None:
    stored = await _merged(graph, c, values, account)
    missing = [f.label for f in c.fields if not stored.get(f.key)]
    if missing:
        raise InvalidConfig(f"Missing: {', '.join(missing)}")
    await graph.run(
        "connector_config_set",
        {"id": account or c.id, "platform": c.id, "label": label,
         "config": security.encrypt(json.dumps(stored)), "by": by, "now": now_ms()},
    )  # fmt: skip


async def clear(graph: Graph, c: Connector, by: str, account: str | None = None) -> None:
    """Disconnect: a first account is cleared; a further account is removed altogether."""
    if account and account != c.id:
        await graph.run("connector_remove", {"id": account})
        return
    await graph.run(
        "connector_config_set",
        {"id": c.id, "platform": c.id, "label": None, "config": "", "by": by, "now": now_ms()},
    )
    await set_teams(graph, c.id, [])  # a reconnected account starts with no name and no teams


async def accounts(graph: Graph, c: Connector) -> list[dict[str, Any]]:
    """Every account of a platform, first account first, with its state and teams."""
    rows = {r["id"]: r for r in await graph.read("connector_list", {}) if r["platform"] == c.id}
    extra = sorted((r for i, r in rows.items() if i != c.id), key=lambda r: str(r["label"] or ""))
    return [rows.get(c.id) or {"id": c.id, "label": None, "teams": []}, *extra]


def new_account_id(c: Connector, label: str, taken: set[str]) -> str:
    """`github:product-github`, unique among the platform's accounts."""
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:40] or "account"
    candidate, n = f"{c.id}:{slug}", 2
    while candidate in taken:
        candidate, n = f"{c.id}:{slug}-{n}", n + 1
    return candidate


async def set_teams(graph: Graph, account: str, teams: list[str]) -> None:
    await graph.run("connector_teams_set", {"id": account, "teams": teams})


async def describe(
    graph: Graph, s: Settings, c: Connector, account: str | None = None
) -> list[dict[str, Any]]:
    """The form for one account: labels and hints, plain values, and secrets as `••••1234` only."""
    stored = await load(graph, account or c.id)
    base = _base(s, c, account or c.id)
    out = []
    for f in c.fields:
        from_app = stored.get(f.key) or ""
        from_env = getattr(base, f.key, None)
        env_value = (
            from_env.get_secret_value() if isinstance(from_env, SecretStr) else str(from_env or "")
        )
        value = from_app or env_value
        out.append(
            {
                "key": f.key,
                "label": f.label,
                "secret": f.secret,
                "placeholder": f.placeholder,
                "hint": f.hint,
                "set": bool(value),
                "value": security.mask(value)
                if f.secret and value
                else ("" if f.secret else value),
                "source": "app" if from_app else ("server" if env_value else None),
            }
        )
    return out
