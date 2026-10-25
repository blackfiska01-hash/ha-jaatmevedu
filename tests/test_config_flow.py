"""Tests for the config flow."""

from __future__ import annotations

import aiohttp
import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.keskkonnateenused.const import API_URL, CONF_CONTRACT_NUMBER, DOMAIN

from .conftest import ADDRESS, CONTRACT


async def _start(hass: HomeAssistant) -> str:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    return str(result["flow_id"])


async def test_success(hass: HomeAssistant, api: AiohttpClientMocker) -> None:  # noqa: ARG001
    flow_id = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        flow_id, {CONF_CONTRACT_NUMBER: " 123 4567 "}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == ADDRESS
    assert result["data"] == {CONF_CONTRACT_NUMBER: CONTRACT}
    assert result["result"].unique_id == CONTRACT


async def test_title_without_address(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(API_URL, json=[])
    flow_id = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        flow_id, {CONF_CONTRACT_NUMBER: CONTRACT}
    )
    assert result["title"] == f"Leping {CONTRACT}"


@pytest.mark.parametrize(
    ("value", "kwargs", "errors"),
    [
        ("12a45", None, {CONF_CONTRACT_NUMBER: "invalid_contract"}),
        (CONTRACT, {"json": {"statusCode": 404}}, {CONF_CONTRACT_NUMBER: "contract_not_found"}),
        (CONTRACT, {"exc": aiohttp.ClientConnectionError()}, {"base": "cannot_connect"}),
    ],
)
async def test_errors_then_recover(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    value: str,
    kwargs: dict[str, object] | None,
    errors: dict[str, str],
) -> None:
    if kwargs is not None:
        aioclient_mock.get(API_URL, **kwargs)
    flow_id = await _start(hass)
    result = await hass.config_entries.flow.async_configure(flow_id, {CONF_CONTRACT_NUMBER: value})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == errors

    aioclient_mock.clear_requests()
    aioclient_mock.get(API_URL, json=[])
    result = await hass.config_entries.flow.async_configure(
        flow_id, {CONF_CONTRACT_NUMBER: CONTRACT}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_already_configured(
    hass: HomeAssistant,
    api: AiohttpClientMocker,  # noqa: ARG001
    entry: MockConfigEntry,
) -> None:
    entry.add_to_hass(hass)
    flow_id = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        flow_id, {CONF_CONTRACT_NUMBER: CONTRACT}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
