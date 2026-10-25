"""Diagnostics for Eesti Keskkonnateenused."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_CONTRACT_NUMBER
from .coordinator import KeskkonnateenusedConfigEntry

TO_REDACT = {CONF_CONTRACT_NUMBER, "address", "title", "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: KeskkonnateenusedConfigEntry
) -> dict[str, Any]:
    """Return diagnostics with the contract number and address removed."""
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "last_update_success": coordinator.last_update_success,
        "discharges": [
            async_redact_data({**asdict(d), "date": d.date.isoformat()}, TO_REDACT)
            for d in coordinator.data or ()
        ],
    }
