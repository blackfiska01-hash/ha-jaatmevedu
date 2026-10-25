"""Calendar of upcoming collections."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import Discharge
from .const import display_name
from .coordinator import KeskkonnateenusedConfigEntry, KeskkonnateenusedCoordinator
from .entity import KeskkonnateenusedEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KeskkonnateenusedConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the collection calendar."""
    async_add_entities([CollectionCalendar(entry.runtime_data)])


class CollectionCalendar(KeskkonnateenusedEntity, CalendarEntity):
    """All-day events for each upcoming collection."""

    _attr_translation_key = "collections"
    _attr_icon = "mdi:delete-clock-outline"

    def __init__(self, coordinator: KeskkonnateenusedCoordinator) -> None:
        super().__init__(coordinator, "calendar")

    def _event(self, discharge: Discharge) -> CalendarEvent:
        language = self.hass.config.language if self.hass else "en"
        return CalendarEvent(
            start=discharge.date,
            end=discharge.date + timedelta(days=1),
            summary=display_name(discharge.waste_type, language),
            description=", ".join(filter(None, (discharge.waste_type, discharge.container))),
            uid=f"{self.coordinator.client.contract_number}-{discharge.date}-{discharge.waste_type}",
        )

    @property
    def event(self) -> CalendarEvent | None:
        discharges = self.coordinator.data or []
        return self._event(discharges[0]) if discharges else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return [
            self._event(d)
            for d in self.coordinator.data or ()
            if dt_util.start_of_local_day(d.date) < end_date
            and dt_util.start_of_local_day(d.date + timedelta(days=1)) > start_date
        ]
