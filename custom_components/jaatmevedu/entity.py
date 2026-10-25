"""Base entity for Eesti jäätmevedu."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_PROVIDER,
    DOMAIN,
    PROVIDER_EKT,
    PROVIDER_MANUFACTURERS,
    PROVIDER_NAMES,
    PROVIDER_URLS,
)
from .coordinator import JaatmeveduCoordinator


class JaatmeveduEntity(CoordinatorEntity[JaatmeveduCoordinator]):
    """Entity bound to one carrier contract or address."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: JaatmeveduCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        base_id = entry.unique_id or entry.entry_id
        provider = entry.data.get(CONF_PROVIDER, PROVIDER_EKT)
        self._attr_unique_id = f"{base_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, base_id)},
            entry_type=DeviceEntryType.SERVICE,
            manufacturer=PROVIDER_MANUFACTURERS[provider],
            name=PROVIDER_NAMES[provider],
            configuration_url=PROVIDER_URLS[provider],
        )
