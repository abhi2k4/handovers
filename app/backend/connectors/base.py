"""The contract every connector implements.

A connector reads one platform's API and returns the same objects an upload produces: `SourceIn`
evidence (with facts, or text the sync service extracts facts from) and, for directory and HR
systems, people. It never writes to the graph itself; `services/sync.py` does, through the same
review gate as uploads. Credentials come from server-side settings or from values an admin entered
in the app (stored encrypted, see services/connector_config.py); never from the browser at sync time.
"""

from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal

import httpx

from core.config import Settings
from ingestion.pipeline import Resolver
from ingestion.schema import SourceIn

Category = Literal["chat", "code", "tickets", "docs", "crm", "directory", "hr"]


class ConnectorError(Exception):
    """A platform call failed. The message is shown to admins, so it never contains a credential."""


@dataclass
class Person:
    """A person as a directory or HR system knows them; matched to employees by email."""

    email: str
    name: str
    title: str | None = None
    manager_email: str | None = None
    department: str | None = None
    status: Literal["active", "incoming", "departed"] = "active"


@dataclass
class Pull:
    sources: list[SourceIn] = field(default_factory=list)
    people: list[Person] = field(default_factory=list)
    cursor: str | None = None  # where the next sync starts (usually the newest timestamp seen)


@dataclass(frozen=True)
class Field:
    """One value an admin enters to connect a platform (a `Settings` attribute)."""

    key: str
    label: str
    secret: bool = False
    placeholder: str = ""
    hint: str = ""


class Connector:
    id: ClassVar[str]
    name: ClassVar[str]
    category: ClassVar[Category]
    # What an admin fills in to connect, in order. Secret fields are stored encrypted and never
    # shown back in full.
    fields: ClassVar[tuple[Field, ...]]

    @property
    def needs(self) -> tuple[str, ...]:
        return tuple(f.key for f in self.fields)

    def configured(self, s: Settings) -> bool:
        return all(present(getattr(s, key, None)) for key in self.needs)

    async def pull(
        self, http: httpx.AsyncClient, s: Settings, res: Resolver, since: str | None
    ) -> Pull:
        raise NotImplementedError

    async def check(self, http: httpx.AsyncClient, s: Settings) -> str:
        """One cheap, read-only call that proves the settings work ("Test connection").

        Returns a short sentence for the admin; raises `ConnectorError` with the reason otherwise.
        """
        raise NotImplementedError


def present(value: Any) -> bool:
    if value is None:
        return False
    if hasattr(value, "get_secret_value"):
        return bool(value.get_secret_value())
    return bool(str(value).strip())


def secret(value: Any) -> str:
    return str(value.get_secret_value()) if hasattr(value, "get_secret_value") else str(value or "")


def csv_list(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]
