"""Data update coordinator for Eesti Keskkonnateenused."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import ContractNotFoundError, Discharge, KeskkonnateenusedClient, KeskkonnateenusedError
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

type KeskkonnateenusedConfigEntry = ConfigEntry[KeskkonnateenusedCoordinator]


class KeskkonnateenusedCoordinator(DataUpdateCoordinator[list[Discharge]]):
    """Polls the provider for the next collection days."""

    config_entry: KeskkonnateenusedConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: KeskkonnateenusedConfigEntry,
        client: KeskkonnateenusedClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> list[Discharge]:
        try:
            discharges = await self.client.async_get_discharges()
        except ContractNotFoundError as err:
            raise ConfigEntryError(
                translation_domain=DOMAIN, translation_key="contract_not_found"
            ) from err
        except KeskkonnateenusedError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
            ) from err

        # The provider keeps a collection listed until its run is processed;
        # anything before today is no longer upcoming.
        today = dt_util.now().date()
        return [d for d in discharges if d.date >= today]
