"""Tests for the config flow."""

from __future__ import annotations

from typing import Any

import aiohttp
import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.jaatmevedu.const import DOMAIN
from custom_components.jaatmevedu.providers import ekt, ragnsells, tjt

from .conftest import ADDRESS, CONTRACT, RS_ROWS, TJT_ADDRESS, TJT_SCHEDULE, rs_page

RS_PICK = "Kose mnt 19\tHabaja alevik, Kose, Harju maakond"


async def _start(hass: HomeAssistant, carrier: str) -> dict[str, Any]:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["ekt", "ragnsells", "tjt"]
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": carrier}
    )


async def _configure(hass: HomeAssistant, result: dict[str, Any], data: dict[str, Any]) -> Any:
    return await hass.config_entries.flow.async_configure(result["flow_id"], data)


# EKT ------------------------------------------------------------------------


async def test_ekt_success(hass: HomeAssistant, api: AiohttpClientMocker) -> None:  # noqa: ARG001
    result = await _start(hass, "ekt")
    assert result["step_id"] == "ekt"
    result = await _configure(hass, result, {"contract_number": " 123 4567 "})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == ADDRESS
    assert result["data"] == {"provider": "ekt", "contract_number": CONTRACT}
    assert result["result"].unique_id == CONTRACT


async def test_ekt_title_without_address(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(ekt.API_URL, json=[])
    result = await _configure(hass, await _start(hass, "ekt"), {"contract_number": CONTRACT})
    assert result["title"] == f"Leping {CONTRACT}"


@pytest.mark.parametrize(
    ("value", "kwargs", "errors"),
    [
        ("12a45", None, {"contract_number": "invalid_contract"}),
        (CONTRACT, {"json": {"statusCode": 404}}, {"contract_number": "contract_not_found"}),
        (CONTRACT, {"exc": aiohttp.ClientConnectionError()}, {"base": "cannot_connect"}),
    ],
)
async def test_ekt_errors_then_recover(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    value: str,
    kwargs: dict[str, object] | None,
    errors: dict[str, str],
) -> None:
    if kwargs is not None:
        aioclient_mock.get(ekt.API_URL, **kwargs)
    result = await _start(hass, "ekt")
    result = await _configure(hass, result, {"contract_number": value})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == errors

    aioclient_mock.clear_requests()
    aioclient_mock.get(ekt.API_URL, json=[])
    result = await _configure(hass, result, {"contract_number": CONTRACT})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_already_configured(
    hass: HomeAssistant,
    api: AiohttpClientMocker,  # noqa: ARG001
    entry: MockConfigEntry,
) -> None:
    entry.add_to_hass(hass)
    result = await _configure(hass, await _start(hass, "ekt"), {"contract_number": CONTRACT})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# Ragn-Sells -------------------------------------------------------------------


async def test_ragnsells_address_search(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(ragnsells.URL, text=rs_page(RS_ROWS))
    result = await _start(hass, "ragnsells")
    assert result["step_id"] == "ragnsells"
    result = await _configure(hass, result, {"area": "463", "search": "Kose mnt"})
    assert result["step_id"] == "pick"
    result = await _configure(hass, result, {"address": RS_PICK})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Kose mnt 19, Habaja alevik, Kose, Harju maakond"
    assert result["data"] == {
        "provider": "ragnsells",
        "area": "463",
        "address": "Kose mnt 19",
        "unit": "Habaja alevik, Kose, Harju maakond",
    }
    assert result["result"].unique_id == (
        "ragnsells_463_kose_mnt_19_habaja_alevik_kose_harju_maakond"
    )


async def test_ragnsells_client_code(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(ragnsells.URL, text=rs_page(RS_ROWS))
    result = await _start(hass, "ragnsells")
    result = await _configure(hass, result, {"area": "463", "client_code": " 12 345 "})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Kose mnt 19, Habaja alevik, Kose, Harju maakond"
    assert result["data"]["client_code"] == "12345"
    assert result["result"].unique_id == "ragnsells_463_12345"


async def test_ragnsells_client_code_without_address(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(
        ragnsells.URL, text=rs_page([("", "", "14", "E", "Olmejäätmed", "02.11.2026")])
    )
    result = await _start(hass, "ragnsells")
    result = await _configure(hass, result, {"area": "463", "client_code": "77"})
    assert result["title"] == "Ragn-Sells 77"


async def test_ragnsells_form_errors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(ragnsells.URL, params={"kl_kood": "999"}, text=rs_page(not_found=True))
    aioclient_mock.get(ragnsells.URL, params={"addr": "Kuhugi"}, text=rs_page(not_found=True))
    aioclient_mock.get(ragnsells.URL, text=rs_page(RS_ROWS))
    result = await _start(hass, "ragnsells")

    result = await _configure(hass, result, {"area": "463"})
    assert result["errors"] == {"base": "missing_query"}
    result = await _configure(hass, result, {"area": "463", "client_code": "999"})
    assert result["errors"] == {"client_code": "not_found"}
    result = await _configure(hass, result, {"area": "463", "search": "Kuhugi"})
    assert result["errors"] == {"search": "no_results"}


async def test_ragnsells_connection_errors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(ragnsells.URL, params={"addr": "Kose"}, exc=aiohttp.ClientError())
    aioclient_mock.get(ragnsells.URL, params={"kl_kood": "1"}, exc=aiohttp.ClientError())
    aioclient_mock.get(ragnsells.URL, text=rs_page(RS_ROWS))
    result = await _start(hass, "ragnsells")
    result = await _configure(hass, result, {"area": "463", "search": "Kose"})
    assert result["errors"] == {"base": "cannot_connect"}
    result = await _configure(hass, result, {"area": "463", "client_code": "1"})
    assert result["errors"] == {"base": "cannot_connect"}


@pytest.mark.parametrize("kwargs", [{"exc": aiohttp.ClientError()}, {"text": "<html></html>"}])
async def test_ragnsells_areas_unavailable(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, kwargs: dict[str, object]
) -> None:
    aioclient_mock.get(ragnsells.URL, **kwargs)
    result = await _start(hass, "ragnsells")
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_pick_fetch_error(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(ragnsells.URL, params={"addr": "Kose mnt 3a"}, exc=aiohttp.ClientError())
    aioclient_mock.get(ragnsells.URL, text=rs_page(RS_ROWS))
    result = await _start(hass, "ragnsells")
    result = await _configure(hass, result, {"area": "463", "search": "Kose mnt"})
    result = await _configure(
        hass, result, {"address": "Kose mnt 3a\tHabaja alevik, Kose, Harju maakond"}
    )
    assert result["step_id"] == "pick"
    assert result["errors"] == {"base": "cannot_connect"}


# TJT ------------------------------------------------------------------------


async def test_tjt(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(
        f"{tjt.BASE_URL}/address",
        params={"address": "Puudub"},
        json={"messages": [], "results": []},
    )
    aioclient_mock.get(
        f"{tjt.BASE_URL}/address", params={"address": "Viga"}, exc=aiohttp.ClientError()
    )
    aioclient_mock.get(f"{tjt.BASE_URL}/address", json={"messages": [], "results": [TJT_ADDRESS]})
    aioclient_mock.get(f"{tjt.BASE_URL}/schedule", json=TJT_SCHEDULE)
    result = await _start(hass, "tjt")
    assert result["step_id"] == "tjt"

    result = await _configure(hass, result, {"area": "Saku vald", "search": "Puudub"})
    assert result["errors"] == {"search": "no_results"}
    result = await _configure(hass, result, {"area": "Saku vald", "search": "Viga"})
    assert result["errors"] == {"base": "cannot_connect"}

    result = await _configure(hass, result, {"area": "Saku vald", "search": "Näidise"})
    assert result["step_id"] == "pick"
    result = await _configure(hass, result, {"address": f"{TJT_ADDRESS}\t"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TJT_ADDRESS
    assert result["data"] == {"provider": "tjt", "area": "Saku vald", "address": TJT_ADDRESS}
    assert result["result"].unique_id.startswith("tjt_saku_vald_harju_maakond")
