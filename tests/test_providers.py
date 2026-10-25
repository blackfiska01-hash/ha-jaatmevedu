"""Tests for the carrier providers."""

from __future__ import annotations

from datetime import date

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.jaatmevedu.providers import (
    Collection,
    NotFoundError,
    ProviderError,
    create_provider,
    ekt,
    ragnsells,
    tjt,
)
from custom_components.jaatmevedu.providers.base import parse_ee_date

from .conftest import ADDRESS, CONTRACT, RS_ROWS, TJT_ADDRESS, TJT_SCHEDULE, ekt_rows, rs_page

# EKT ------------------------------------------------------------------------


async def test_ekt_fetch(hass: HomeAssistant, api: AiohttpClientMocker) -> None:
    provider = ekt.EktProvider(async_get_clientsession(hass), CONTRACT)
    result = await provider.async_fetch()
    assert result[0] == Collection(
        date=date(2026, 10, 28),
        waste_type="Segaolmejäätmed",
        address=ADDRESS,
        container="0,24 m3 plastikkonteiner",
    )
    assert len(result) == 2
    assert api.mock_calls[0][1].query["contractNumber"] == CONTRACT


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"json": {"statusCode": 404, "message": "Contract not found"}}, NotFoundError),
        ({"json": {"statusCode": 500, "message": "boom"}}, ProviderError),
        ({"json": "nope"}, ProviderError),
        ({"status": 502}, ProviderError),
        ({"text": "<html>"}, ProviderError),
        ({"exc": aiohttp.ClientConnectionError()}, ProviderError),
        ({"exc": TimeoutError()}, ProviderError),
    ],
)
async def test_ekt_errors(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    kwargs: dict[str, object],
    error: type[Exception],
) -> None:
    aioclient_mock.get(ekt.API_URL, **kwargs)
    with pytest.raises(error):
        await ekt.EktProvider(async_get_clientsession(hass), CONTRACT).async_fetch()


def test_ekt_parse_skips_bad_rows_and_duplicates() -> None:
    items = [
        *ekt_rows(
            ("2026-11-04", "Pakendid", "kott"),
            ("2026-10-28", "Segaolmejäätmed", "0,24 m3"),
            ("2026-10-28", "Segaolmejäätmed", "0,24 m3"),
            ("not-a-date", "Segaolmejäätmed", "0,24 m3"),
            ("2026-10-30", "", ""),
        ),
        {"date": "2026-10-29T00:00:00", "itemType": "Konteiner"},
        "garbage",
    ]
    assert [(c.date.isoformat(), c.waste_type) for c in ekt.parse(items)] == [
        ("2026-10-28", "Segaolmejäätmed"),
        ("2026-10-29", "Konteiner"),
        ("2026-11-04", "Pakendid"),
    ]


def test_parse_ee_date() -> None:
    assert parse_ee_date("28.10.2026") == date(2026, 10, 28)
    assert parse_ee_date("2026-10-28") == date(2026, 10, 28)
    assert parse_ee_date("31.02.2026") is None
    assert parse_ee_date("") is None


# Ragn-Sells -------------------------------------------------------------------


async def test_ragnsells_areas_and_search(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(ragnsells.URL, text=rs_page(RS_ROWS))
    session = async_get_clientsession(hass)
    assert await ragnsells.async_get_areas(session) == {
        "463": "Kose vald",
        "521": "Pärnu linn 1 piirkond",
    }
    matches = await ragnsells.async_search(session, "463", "Kose mnt, Habaja alevik long query")
    assert [m.label for m in matches] == [
        "Kose mnt 19, Habaja alevik, Kose, Harju maakond",
        "Kose mnt 3a, Habaja alevik, Kose, Harju maakond",
    ]
    query = aioclient_mock.mock_calls[-1][1].query
    assert query["piirkond"] == "463"
    assert len(query["addr"]) == ragnsells.MAX_QUERY


async def test_ragnsells_fetch_by_address(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(ragnsells.URL, text=rs_page(RS_ROWS))
    provider = ragnsells.RagnSellsProvider(
        async_get_clientsession(hass),
        "463",
        address="Kose mnt 19",
        unit="Habaja alevik, Kose, Harju maakond",
    )
    result = await provider.async_fetch()
    assert result == [
        Collection(
            date=date(2026, 10, 29),
            waste_type="Olmejäätmed",
            address="Kose mnt 19, Habaja alevik, Kose, Harju maakond",
            frequency_days=28,
            weekdays=("thu", "mon"),
        ),
        Collection(
            date=date(2026, 11, 2),
            waste_type="Biolagunevad jäätmed",
            address="Kose mnt 19, Habaja alevik, Kose, Harju maakond",
            frequency_days=14,
            weekdays=("mon",),
        ),
    ]


async def test_ragnsells_fetch_by_client_code(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(ragnsells.URL, text=rs_page(RS_ROWS))
    provider = ragnsells.RagnSellsProvider(
        async_get_clientsession(hass), "463", client_code="12345"
    )
    assert len(await provider.async_fetch()) == 3
    assert aioclient_mock.mock_calls[-1][1].query["kl_kood"] == "12345"


async def test_ragnsells_not_found(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(ragnsells.URL, text=rs_page(not_found=True))
    provider = ragnsells.RagnSellsProvider(
        async_get_clientsession(hass), "463", address="Kuhugi 1", unit="X"
    )
    with pytest.raises(NotFoundError):
        await provider.async_fetch()


def test_ragnsells_parse_skips_bad_rows() -> None:
    rows = [
        ["short"],
        ["A 1", "U", "", "", "Olmejäätmed", "bad"],
        ["A 1", "", "x", "", "Paber", "01.12.2026"],
    ]
    assert ragnsells.rows_to_collections(rows) == [
        Collection(date=date(2026, 12, 1), waste_type="Paber", address="A 1")
    ]


# TJT ------------------------------------------------------------------------


async def test_tjt_search_and_fetch(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(
        f"{tjt.BASE_URL}/address", json={"messages": [], "results": [TJT_ADDRESS, 5]}
    )
    aioclient_mock.get(f"{tjt.BASE_URL}/schedule", json=TJT_SCHEDULE)
    session = async_get_clientsession(hass)
    matches = await tjt.async_search(session, "Saku vald", "Näidise")
    assert [m.label for m in matches] == [TJT_ADDRESS]

    result = await tjt.TjtProvider(session, TJT_ADDRESS).async_fetch()
    assert [(c.date.isoformat(), c.waste_type, c.frequency_days, c.weekdays) for c in result] == [
        ("2026-10-26", "Segaolmejäätmed", None, ("mon",)),
        ("2026-10-28", "Biojäätmed", 14, ("wed",)),
        ("2026-10-28", "Segaolmejäätmed", None, ("wed",)),
        ("2026-11-11", "Biojäätmed", 14, ("wed",)),
    ]


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        ({"messages": ["Aadressi ei leitud"], "results": []}, NotFoundError),
        ([1, 2], ProviderError),
    ],
)
async def test_tjt_errors(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    payload: object,
    error: type[Exception],
) -> None:
    aioclient_mock.get(f"{tjt.BASE_URL}/schedule", json=payload)
    with pytest.raises(error):
        await tjt.TjtProvider(async_get_clientsession(hass), TJT_ADDRESS).async_fetch()


def test_tjt_parse_skips_bad_rows() -> None:
    assert tjt.parse({"results": []}) == []
    payload = {
        "results": {
            "address": "A",
            "rows": ["x", ["1", "E"], ["1", "E", "", "01.01.2027"], ["1", "E", "Paber", "nope"]],
        }
    }
    assert tjt.parse(payload) == []


async def test_tjt_empty_without_message(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(f"{tjt.BASE_URL}/schedule", json={"messages": [], "results": []})
    assert await tjt.TjtProvider(async_get_clientsession(hass), TJT_ADDRESS).async_fetch() == []


async def test_create_provider(hass: HomeAssistant) -> None:
    session = async_get_clientsession(hass)
    assert isinstance(create_provider(session, {"contract_number": "1"}), ekt.EktProvider)
    rs = create_provider(session, {"provider": "ragnsells", "area": "463", "client_code": "9"})
    assert isinstance(rs, ragnsells.RagnSellsProvider)
    assert rs.client_code == "9"
    assert isinstance(
        create_provider(session, {"provider": "tjt", "address": TJT_ADDRESS}), tjt.TjtProvider
    )
