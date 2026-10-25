"""Sensors for Eesti Keskkonnateenused."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import Discharge
from .const import CATEGORY_ICONS, display_name, waste_category
from .coordinator import KeskkonnateenusedConfigEntry, KeskkonnateenusedCoordinator
from .entity import KeskkonnateenusedEntity

PARALLEL_UPDATES = 0


def _days_until(when: date | None) -> int | None:
    if when is None:
        return None
    return (when - dt_util.now().date()).days


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_") or "waste"


def waste_key(waste_type: str) -> str:
    """Stable key for a waste type: its category, or a slug of the provider's name."""
    return waste_category(waste_type) or _slug(waste_type)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KeskkonnateenusedConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors, adding one per waste type as types appear."""
    coordinator = entry.runtime_data
    async_add_entities([NextCollectionSensor(coordinator), DaysUntilSensor(coordinator)])

    known: set[str] = set()

    @callback
    def _add_new_waste_types() -> None:
        new: list[WasteTypeSensor] = []
        for discharge in coordinator.data or ():
            key = waste_key(discharge.waste_type)
            if key not in known:
                known.add(key)
                new.append(WasteTypeSensor(coordinator, key, discharge.waste_type))
        if new:
            async_add_entities(new)

    _add_new_waste_types()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_waste_types))


def _next(discharges: list[Discharge]) -> list[Discharge]:
    """All discharges on the earliest upcoming day."""
    if not discharges:
        return []
    first = min(d.date for d in discharges)
    return [d for d in discharges if d.date == first]


class NextCollectionSensor(KeskkonnateenusedEntity, SensorEntity):
    """Date of the next collection of any waste type."""

    _attr_device_class = SensorDeviceClass.DATE
    _attr_translation_key = "next_collection"
    _attr_icon = "mdi:trash-can-outline"

    def __init__(self, coordinator: KeskkonnateenusedCoordinator) -> None:
        super().__init__(coordinator, "next_collection")

    @property
    def native_value(self) -> date | None:
        upcoming = _next(self.coordinator.data or [])
        return upcoming[0].date if upcoming else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        upcoming = _next(self.coordinator.data or [])
        language = self.hass.config.language if self.hass else "en"
        return {
            "waste_types": [display_name(d.waste_type, language) for d in upcoming],
            "days_until": _days_until(upcoming[0].date) if upcoming else None,
        }


class DaysUntilSensor(KeskkonnateenusedEntity, SensorEntity):
    """Days left until the next collection (0 = today)."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_suggested_display_precision = 0
    _attr_translation_key = "days_until_next"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: KeskkonnateenusedCoordinator) -> None:
        super().__init__(coordinator, "days_until_next")

    @property
    def native_value(self) -> int | None:
        upcoming = _next(self.coordinator.data or [])
        return _days_until(upcoming[0].date) if upcoming else None


class WasteTypeSensor(KeskkonnateenusedEntity, SensorEntity):
    """Next collection date for one waste type."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(
        self, coordinator: KeskkonnateenusedCoordinator, key: str, waste_type: str
    ) -> None:
        super().__init__(coordinator, f"waste_{key}")
        self._key = key
        category = waste_category(waste_type)
        if category is not None:
            self._attr_translation_key = category
        else:
            self._attr_name = waste_type
        self._attr_icon = CATEGORY_ICONS[category]

    def _mine(self) -> list[Discharge]:
        return [d for d in self.coordinator.data or () if waste_key(d.waste_type) == self._key]

    @property
    def native_value(self) -> date | None:
        mine = self._mine()
        return min(d.date for d in mine) if mine else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        mine = self._mine()
        first = min(mine, key=lambda d: d.date) if mine else None
        return {
            "waste_type": first.waste_type if first else None,
            "container": first.container if first else None,
            "days_until": _days_until(first.date if first else None),
        }
