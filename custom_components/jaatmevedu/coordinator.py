"""Data update coordinator for Eesti jäätmevedu."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, UPDATE_INTERVAL
from .providers import Collection, NotFoundError, Provider, ProviderError

_LOGGER = logging.getLogger(__name__)

type JaatmeveduConfigEntry = ConfigEntry[JaatmeveduCoordinator]


class JaatmeveduCoordinator(DataUpdateCoordinator[list[Collection]]):
    """Polls one carrier for the upcoming collection days."""

    config_entry: JaatmeveduConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: JaatmeveduConfigEntry,
        provider: Provider,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.provider = provider

    async def _async_update_data(self) -> list[Collection]:
        try:
            collections = await self.provider.async_fetch()
        except NotFoundError as err:
            raise ConfigEntryError(translation_domain=DOMAIN, translation_key="not_found") from err
        except ProviderError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
            ) from err

        # A collection stays listed until the carrier processes its run;
        # anything before today is no longer upcoming.
        today = dt_util.now().date()
        return [c for c in collections if c.date >= today]
