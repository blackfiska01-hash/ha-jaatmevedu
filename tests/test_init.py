"""Tests for setup, unload, sensors, calendar and diagnostics."""

from __future__ import annotations

from datetime import timedelta

import aiohttp
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.keskkonnateenused.const import API_URL, UPDATE_INTERVAL

from .conftest import ADDRESS, CONTRACT, rows

TODAY = "2026-10-25 12:00:00+02:00"


def _ids(hass: HomeAssistant) -> dict[str, str]:
    registry = er.async_get(hass)
    return {
        str(e.unique_id): e.entity_id
        for e in registry.entities.values()
        if e.platform == "keskkonnateenused"
    }


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.config.async_set_time_zone("Europe/Tallinn")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_sensors(
    hass: HomeAssistant,
    api: AiohttpClientMocker,  # noqa: ARG001
    entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    freezer.move_to(TODAY)
    await _setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED

    ids = _ids(hass)
    nxt = hass.states.get(ids[f"{CONTRACT}_next_collection"])
    assert nxt is not None
    assert nxt.state == "2026-10-28"
    assert nxt.attributes["waste_types"] == ["Mixed waste"]
    assert nxt.attributes["days_until"] == 3

    days = hass.states.get(ids[f"{CONTRACT}_days_until_next"])
    assert days is not None
    assert days.state == "3"

    mixed = hass.states.get(ids[f"{CONTRACT}_waste_mixed"])
    assert mixed is not None
    assert mixed.state == "2026-10-28"
    assert mixed.attributes["container"] == "0,24 m3 plastikkonteiner"
    assert mixed.attributes["waste_type"] == "Segaolmejäätmed"
    assert mixed.attributes["icon"] == "mdi:trash-can"
    assert mixed.attributes["friendly_name"] == "Eesti Keskkonnateenused Mixed waste"

    packaging = hass.states.get(ids[f"{CONTRACT}_waste_packaging"])
    assert packaging is not None
    assert packaging.state == "2026-11-04"
    assert packaging.attributes["days_until"] == 10


async def test_new_and_unknown_types_and_midnight(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    freezer.move_to(TODAY)
    aioclient_mock.get(API_URL, json=rows(("2026-10-28", "Segaolmejäätmed", "0,24 m3")))
    await _setup(hass, entry)
    assert f"{CONTRACT}_waste_midagi_uut" not in _ids(hass)

    aioclient_mock.clear_requests()
    aioclient_mock.get(
        API_URL,
        json=rows(("2026-10-28", "Segaolmejäätmed", "0,24 m3"), ("2026-10-29", "Midagi uut", "")),
    )
    freezer.tick(UPDATE_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    new = hass.states.get(_ids(hass)[f"{CONTRACT}_waste_midagi_uut"])
    assert new is not None
    assert new.attributes["friendly_name"] == "Eesti Keskkonnateenused Midagi uut"
    assert new.attributes["icon"] == "mdi:trash-can-outline"

    # On collection day the date counts as today; the day after it is dropped.
    freezer.move_to("2026-10-28 00:05:00+02:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(_ids(hass)[f"{CONTRACT}_days_until_next"]).state == "0"  # type: ignore[union-attr]

    freezer.move_to("2026-10-29 00:05:00+02:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    ids = _ids(hass)
    assert hass.states.get(ids[f"{CONTRACT}_waste_mixed"]).state == "unknown"  # type: ignore[union-attr]
    assert hass.states.get(ids[f"{CONTRACT}_next_collection"]).state == "2026-10-29"  # type: ignore[union-attr]


async def test_empty_response(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    entry: MockConfigEntry,
) -> None:
    aioclient_mock.get(API_URL, json=[])
    await _setup(hass, entry)
    ids = _ids(hass)
    assert hass.states.get(ids[f"{CONTRACT}_next_collection"]).state == "unknown"  # type: ignore[union-attr]
    assert hass.states.get(ids[f"{CONTRACT}_days_until_next"]).state == "unknown"  # type: ignore[union-attr]
    assert hass.states.get(ids[f"{CONTRACT}_calendar"]).state == "off"  # type: ignore[union-attr]


async def test_setup_retry_and_failure(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    entry: MockConfigEntry,
) -> None:
    aioclient_mock.get(API_URL, exc=aiohttp.ClientConnectionError())
    await _setup(hass, entry)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_contract_gone(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    entry: MockConfigEntry,
) -> None:
    aioclient_mock.get(API_URL, json={"statusCode": 404, "message": "Contract not found"})
    await _setup(hass, entry)
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_unload(
    hass: HomeAssistant,
    api: AiohttpClientMocker,  # noqa: ARG001
    entry: MockConfigEntry,
) -> None:
    await _setup(hass, entry)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_calendar(
    hass: HomeAssistant,
    api: AiohttpClientMocker,  # noqa: ARG001
    entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    freezer.move_to(TODAY)
    await _setup(hass, entry)
    calendar_id = _ids(hass)[f"{CONTRACT}_calendar"]

    state = hass.states.get(calendar_id)
    assert state is not None
    assert state.attributes["message"] == "Mixed waste"
    assert state.attributes["start_time"] == "2026-10-28 00:00:00"

    start = dt_util.now()
    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": calendar_id, "start_date_time": start, "duration": {"days": 7}},
        blocking=True,
        return_response=True,
    )
    events = response[calendar_id]["events"]  # type: ignore[index]
    assert [(e["start"], e["summary"]) for e in events] == [("2026-10-28", "Mixed waste")]
    assert events[0]["description"] == "Segaolmejäätmed, 0,24 m3 plastikkonteiner"

    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": calendar_id,
            "start_date_time": start + timedelta(days=10),
            "duration": {"hours": 2},
        },
        blocking=True,
        return_response=True,
    )
    assert [e["summary"] for e in response[calendar_id]["events"]] == ["Packaging"]  # type: ignore[index]


async def test_russian_names(
    hass: HomeAssistant,
    api: AiohttpClientMocker,  # noqa: ARG001
    entry: MockConfigEntry,
) -> None:
    await hass.config.async_update(language="ru")
    await _setup(hass, entry)
    ids = _ids(hass)
    state = hass.states.get(ids[f"{CONTRACT}_next_collection"])
    assert state is not None
    assert state.attributes["waste_types"] == ["Смешанные отходы"]


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    api: AiohttpClientMocker,  # noqa: ARG001
    entry: MockConfigEntry,
) -> None:
    await _setup(hass, entry)
    result = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    text = str(result)
    assert CONTRACT not in text
    assert ADDRESS not in text
    assert result["discharges"][0]["waste_type"] == "Segaolmejäätmed"
    assert result["discharges"][0]["date"] == "2026-10-28"
