"""Bewegungsmelder (Kamera des Bilderrahmens)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import LumoraConfigEntry
from .const import MOTION_HOLD_SECONDS
from .entity import LumoraEntity


async def async_setup_entry(hass: HomeAssistant, entry: LumoraConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([LumoraMotion(entry.runtime_data.coordinator, "motion")])


class LumoraMotion(LumoraEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.MOTION

    @property
    def available(self) -> bool:
        return super().available and bool(self.coordinator.data.get("motionEnabled"))

    @property
    def is_on(self) -> bool:
        last = self.coordinator.data.get("lastMotion")
        when = dt_util.parse_datetime(last) if isinstance(last, str) else None
        return bool(when and (dt_util.utcnow() - when).total_seconds() < MOTION_HOLD_SECONDS)

    @property
    def extra_state_attributes(self):
        return {"last_motion": self.coordinator.data.get("lastMotion")}
