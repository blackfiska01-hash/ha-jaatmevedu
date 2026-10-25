"""Diagnostics for Eesti jäätmevedu."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_ADDRESS, CONF_CLIENT_CODE, CONF_CONTRACT_NUMBER, CONF_UNIT
from .coordinator import JaatmeveduConfigEntry

TO_REDACT = {
    CONF_CONTRACT_NUMBER,
    CONF_CLIENT_CODE,
    CONF_ADDRESS,
    CONF_UNIT,
    "title",
    "unique_id",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: JaatmeveduConfigEntry
) -> dict[str, Any]:
    """Return diagnostics with contract numbers, client codes and addresses removed."""
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "last_update_success": coordinator.last_update_success,
        "collections": [
            async_redact_data({**asdict(c), "date": c.date.isoformat()}, TO_REDACT)
            for c in coordinator.data or ()
        ],
    }
