"""Base entity for Eesti Keskkonnateenused."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import KeskkonnateenusedCoordinator


class KeskkonnateenusedEntity(CoordinatorEntity[KeskkonnateenusedCoordinator]):
    """Entity bound to one contract's device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: KeskkonnateenusedCoordinator, key: str) -> None:
        super().__init__(coordinator)
        contract_number = coordinator.client.contract_number
        self._attr_unique_id = f"{contract_number}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, contract_number)},
            entry_type=DeviceEntryType.SERVICE,
            manufacturer=MANUFACTURER,
            name="Eesti Keskkonnateenused",
            configuration_url="https://eteenindus.keskkonnateenused.ee/",
        )
