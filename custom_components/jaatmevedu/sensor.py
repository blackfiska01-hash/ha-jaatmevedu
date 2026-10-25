"""Sensors for Eesti jäätmevedu."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import CATEGORY_ICONS, display_name, waste_category
from .coordinator import JaatmeveduConfigEntry, JaatmeveduCoordinator
from .entity import JaatmeveduEntity
from .providers import Collection

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
    entry: JaatmeveduConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors, adding one per waste type as types appear."""
    coordinator = entry.runtime_data
    async_add_entities([NextCollectionSensor(coordinator), DaysUntilSensor(coordinator)])

    known: set[str] = set()

    @callback
    def _add_new_waste_types() -> None:
        new: list[WasteTypeSensor] = []
        for collection in coordinator.data or ():
            key = waste_key(collection.waste_type)
            if key not in known:
                known.add(key)
                new.append(WasteTypeSensor(coordinator, key, collection.waste_type))
        if new:
            async_add_entities(new)

    _add_new_waste_types()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_waste_types))


def _next(collections: list[Collection]) -> list[Collection]:
    """All collections on the earliest upcoming day."""
    if not collections:
        return []
    first = min(d.date for d in collections)
    return [d for d in collections if d.date == first]


class NextCollectionSensor(JaatmeveduEntity, SensorEntity):
    """Date of the next collection of any waste type."""

    _attr_device_class = SensorDeviceClass.DATE
    _attr_translation_key = "next_collection"
    _attr_icon = "mdi:trash-can-outline"

    def __init__(self, coordinator: JaatmeveduCoordinator) -> None:
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
            "waste_types": list(
                dict.fromkeys(display_name(d.waste_type, language) for d in upcoming)
            ),
            "days_until": _days_until(upcoming[0].date) if upcoming else None,
        }


class DaysUntilSensor(JaatmeveduEntity, SensorEntity):
    """Days left until the next collection (0 = today)."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_suggested_display_precision = 0
    _attr_translation_key = "days_until_next"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: JaatmeveduCoordinator) -> None:
        super().__init__(coordinator, "days_until_next")

    @property
    def native_value(self) -> int | None:
        upcoming = _next(self.coordinator.data or [])
        return _days_until(upcoming[0].date) if upcoming else None


class WasteTypeSensor(JaatmeveduEntity, SensorEntity):
    """Next collection date for one waste type."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: JaatmeveduCoordinator, key: str, waste_type: str) -> None:
        super().__init__(coordinator, f"waste_{key}")
        self._key = key
        category = waste_category(waste_type)
        if category is not None:
            self._attr_translation_key = category
        else:
            self._attr_name = waste_type
        self._attr_icon = CATEGORY_ICONS[category]

    def _mine(self) -> list[Collection]:
        return [d for d in self.coordinator.data or () if waste_key(d.waste_type) == self._key]

    @property
    def native_value(self) -> date | None:
        mine = self._mine()
        return min(d.date for d in mine) if mine else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        mine = self._mine()
        first = min(mine, key=lambda d: d.date) if mine else None
        if first is None:
            return {"days_until": None}
        attrs: dict[str, Any] = {
            "waste_type": first.waste_type,
            "days_until": _days_until(first.date),
        }
        if first.container:
            attrs["container"] = first.container
        if first.frequency_days:
            attrs["frequency_days"] = first.frequency_days
        if first.weekdays:
            attrs["weekdays"] = list(first.weekdays)
        return attrs
