"""Tests for the API client."""

from __future__ import annotations

from datetime import date

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.keskkonnateenused.api import (
    ContractNotFoundError,
    Discharge,
    KeskkonnateenusedClient,
    KeskkonnateenusedError,
    parse_discharges,
)
from custom_components.keskkonnateenused.const import API_URL

from .conftest import ADDRESS, CONTRACT, rows


async def test_fetch(hass: HomeAssistant, api: AiohttpClientMocker) -> None:
    client = KeskkonnateenusedClient(async_get_clientsession(hass), CONTRACT)
    result = await client.async_get_discharges()
    assert result[0] == Discharge(
        date=date(2026, 10, 28),
        waste_type="Segaolmejäätmed",
        container="0,24 m3 plastikkonteiner",
        address=ADDRESS,
    )
    assert len(result) == 2
    assert api.mock_calls[0][1].query["contractNumber"] == CONTRACT


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"json": {"statusCode": 404, "message": "Contract not found"}}, ContractNotFoundError),
        ({"json": {"statusCode": 500, "message": "boom"}}, KeskkonnateenusedError),
        ({"json": "nope"}, KeskkonnateenusedError),
        ({"status": 502}, KeskkonnateenusedError),
        ({"text": "<html>"}, KeskkonnateenusedError),
        ({"exc": aiohttp.ClientConnectionError()}, KeskkonnateenusedError),
        ({"exc": TimeoutError()}, KeskkonnateenusedError),
    ],
)
async def test_errors(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    kwargs: dict[str, object],
    error: type[Exception],
) -> None:
    aioclient_mock.get(API_URL, **kwargs)
    client = KeskkonnateenusedClient(async_get_clientsession(hass), CONTRACT)
    with pytest.raises(error):
        await client.async_get_discharges()


def test_parse_skips_bad_rows_and_duplicates() -> None:
    items = [
        *rows(
            ("2026-11-04", "Pakendid", "kott"),
            ("2026-10-28", "Segaolmejäätmed", "0,24 m3"),
            ("2026-10-28", "Segaolmejäätmed", "0,24 m3"),
            ("not-a-date", "Segaolmejäätmed", "0,24 m3"),
            ("2026-10-30", "", ""),
        ),
        {"date": "2026-10-29T00:00:00", "itemType": "Konteiner"},
        "garbage",
    ]
    result = parse_discharges(items)
    assert [(d.date.isoformat(), d.waste_type) for d in result] == [
        ("2026-10-28", "Segaolmejäätmed"),
        ("2026-10-29", "Konteiner"),
        ("2026-11-04", "Pakendid"),
    ]
