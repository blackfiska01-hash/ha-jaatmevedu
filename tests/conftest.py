"""Shared fixtures for the Eesti Keskkonnateenused tests."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.keskkonnateenused.const import API_URL, CONF_CONTRACT_NUMBER, DOMAIN

pytest_plugins = ["pytest_homeassistant_custom_component"]

CONTRACT = "1234567"
ADDRESS = "Näidise tn 1, Tallinn, Harju maakond"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading of custom_components/ in every test."""


def rows(*items: tuple[str, str, str]) -> list[dict[str, Any]]:
    """Build API rows from (date, garbage, itemType) tuples."""
    return [
        {"address": ADDRESS, "contractNumber": CONTRACT, "date": d, "garbage": g, "itemType": t}
        for d, g, t in items
    ]


DEFAULT_ROWS = rows(
    ("2026-10-28", "Segaolmejäätmed", "0,24 m3 plastikkonteiner"),
    ("2026-11-04", "Segapakendid", "0,24 m3 plastikkonteiner"),
)


@pytest.fixture
def api(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """Answer the lookup with two upcoming collections."""
    aioclient_mock.get(API_URL, json=DEFAULT_ROWS)
    return aioclient_mock


@pytest.fixture
def entry() -> MockConfigEntry:
    """A config entry for the test contract."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=ADDRESS,
        unique_id=CONTRACT,
        data={CONF_CONTRACT_NUMBER: CONTRACT},
    )
