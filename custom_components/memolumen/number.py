"""Helligkeit des Bilderrahmens."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MemolumenConfigEntry
from .entity import MemolumenEntity


async def async_setup_entry(hass: HomeAssistant, entry: MemolumenConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([MemolumenBrightness(entry.runtime_data.coordinator, "brightness")])


class MemolumenBrightness(MemolumenEntity, NumberEntity):
    _attr_icon = "mdi:brightness-6"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.data.get("brightness")
        return None if value is None else float(value)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.api.set_brightness(int(round(value)))
        await self._refresh()
