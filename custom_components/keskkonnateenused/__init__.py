"""The Eesti Keskkonnateenused integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change

from .api import KeskkonnateenusedClient
from .const import CONF_CONTRACT_NUMBER
from .coordinator import KeskkonnateenusedConfigEntry, KeskkonnateenusedCoordinator

PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: KeskkonnateenusedConfigEntry) -> bool:
    """Set up a contract from a config entry."""
    client = KeskkonnateenusedClient(
        async_get_clientsession(hass), entry.data[CONF_CONTRACT_NUMBER]
    )
    coordinator = KeskkonnateenusedCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    @callback
    def _refresh_after_midnight(_now: datetime) -> None:
        # "Days until" and today's filtering change at midnight, not on the poll schedule.
        hass.async_create_task(coordinator.async_request_refresh())

    entry.async_on_unload(
        async_track_time_change(hass, _refresh_after_midnight, hour=0, minute=5, second=0)
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KeskkonnateenusedConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
