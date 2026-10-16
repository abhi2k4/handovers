"""Alerts against a seeded graph: settings, notify, inbox, reminders' last time, recipients."""

import json
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from core.config import Settings
from core.falkordb import FalkorDBClient
from core.graph import Graph, QueryCatalog
from seed.load import bootstrap, load, open_scenario
from services import access, alerts

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def graph() -> AsyncIterator[Graph]:
    settings = Settings(handovers_tenant="itest_alerts")
    client = FalkorDBClient(settings)
    if not (await client.status()).ok:
        await client.close()
        pytest.skip("FalkorDB not reachable")
    if await client.graph_exists():
        await client.graph().delete()
    g = Graph(client, QueryCatalog(settings.graph_dir))
    await bootstrap(g)
    await load(g)
    await open_scenario(g)
    yield g
    await client.graph().delete()
    await client.close()


@pytest.mark.asyncio(loop_scope="module")
async def test_settings_round_trip_and_hr_recipients(graph: Graph) -> None:
    await alerts.save_settings(
        graph, "emp:meera", {"phone": "919876543210", "modes": {"candidate": "off"}}
    )
    s = await alerts.settings_for(graph, "emp:meera")
    assert s["phone"] == "919876543210" and s["modes"]["candidate"] == "off"
    assert s["modes"]["reminder"] == "instant" and s["quiet_from"] == 21
    hr = {r["id"] for r in await access.hr_people(graph)}
    assert "emp:meera" in hr


@pytest.mark.asyncio(loop_scope="module")
async def test_notify_records_inbox_and_last_reminder(graph: Graph) -> None:
    hid = (await graph.read("handover_list", {}))[0]["id"]
    off = await alerts.notify(graph, "candidate", "emp:meera", "x", "y")
    assert off["status"] == "off"
    sent = await alerts.notify(
        graph,
        "reminder",
        "emp:nisha",
        "Exit interview?",
        "Meera reminded you",
        [{"id": "open:/h", "label": "Open"}],
        "/h",
        hid,
        "interview",
    )
    assert sent["status"] == "app"  # no WhatsApp configured in tests
    inbox = await graph.read("alert_list", {"to": "emp:nisha"})
    assert inbox[0]["id"] == sent["id"] and inbox[0]["handover"] == hid
    assert json.loads(inbox[0]["buttons"])[0]["label"] == "Open"
    last = await graph.read("alert_last_reminder", {"handover": hid})
    assert [r["step"] for r in last] == ["interview"]
    await graph.run("alert_act", {"id": sent["id"], "acted": "open:/h", "now": 1})
    assert (await graph.one("alert_get", {"id": sent["id"]}) or {})["acted"] == "open:/h"


@pytest.mark.asyncio(loop_scope="module")
async def test_clearance_rows_and_graph_resolution(graph: Graph) -> None:
    from core.clock import now_ms
    from services import clearance

    hid = (await graph.read("handover_list", {}))[0]["id"]
    items = await clearance.load(graph, hid)  # created when the handover opened
    keys = [i["key"] for i in items]
    assert (
        "admin:acc:mixpanel" in keys and "asset:laptop" in keys and "work:resp:utm-rebuild" in keys
    )
    assert clearance.counts(items)[0] == 0
    await graph.run(
        "account_reassign",
        {
            "account": "acc:mixpanel",
            "to": "emp:aditi",
            "handover": hid,
            "now": now_ms(),
            "open": 253402300799000,
            "leaver_until": 253402300799000,
        },
    )
    await graph.run(
        "clearance_set",
        {
            "handover": hid,
            "key": "asset:laptop",
            "status": "confirmed",
            "by": "Meera",
            "now": now_ms(),
        },
    )
    by = {i["key"]: i for i in await clearance.load(graph, hid)}
    assert (
        by["admin:acc:mixpanel"]["status"] == "confirmed"
        and by["admin:acc:mixpanel"]["by"] == "Aditi Menon"
    )
    assert by["asset:laptop"]["status"] == "confirmed" and not by["asset:laptop"]["auto"]
    assert await clearance.tally(graph, hid) == (2, len(by))


@pytest.mark.asyncio(loop_scope="module")
async def test_candidates_store_once_per_person(graph: Graph) -> None:
    from services import candidates

    hid = (await graph.read("handover_list", {}))[0]["id"]
    rows = candidates.screen(
        candidates.parse("Name,Mobile\nKavita Joshi,9000000104\n"), [], hid, "WorkIndia"
    )
    for _ in range(2):
        await graph.run("candidate_add", {"handover": hid, "rows": rows, "now": 1})
    listed = await graph.read("candidate_list", {"handover": hid})
    assert [c["name"] for c in listed] == ["Kavita Joshi"] and listed[0]["source"] == "WorkIndia"
