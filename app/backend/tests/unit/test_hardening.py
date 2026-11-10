"""Request-level guards that need no graph: anonymous writes, follow-up parsing, LLM output."""

import asyncio
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from api.deps import get_caller
from core.config import get_settings
from services import access
from services.access import Caller
from services.companion import is_follow_up


@pytest.fixture
def sso(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("KEYCLOAK_URL", "http://keycloak:8180")
    monkeypatch.setenv("ALLOW_GUEST", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _request(method: str) -> Request:
    app = SimpleNamespace(state=SimpleNamespace(graph=None))  # no cookie: the graph is not read
    return Request({"type": "http", "method": method, "headers": [], "path": "/api/x", "app": app})


def test_with_sign_in_on_an_anonymous_request_can_read_but_not_write(sso: None) -> None:
    # Leaving the View-as header out must not unlock the platform admin's actions.
    assert asyncio.run(get_caller(_request("GET"), None)) is None
    for method in ("POST", "PUT", "DELETE"):
        with pytest.raises(HTTPException) as err:
            asyncio.run(get_caller(_request(method), None))
        assert err.value.status_code == 401


def test_only_hr_curates_sources() -> None:
    hr = Caller(id="emp:meera", name="Meera", title="HR", team=None, roles=frozenset({"hr"}))
    dev = Caller(id="emp:arjun", name="Arjun", title="Dev", team=None, roles=frozenset())
    assert access.can_curate_sources(hr)
    assert not access.can_curate_sources(dev)


def test_a_numbers_only_follow_up_does_not_crash() -> None:
    for q in ("123", "2026?", "₹500"):
        assert is_follow_up(q) in (True, False)
