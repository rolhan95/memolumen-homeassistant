"""Sensoren: Umgebungslicht, Anzahl Fotos, nächste Einschaltzeit."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import LIGHT_LUX, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import MemolumenConfigEntry
from .entity import MemolumenEntity


def _ts(value: Any):
    return dt_util.parse_datetime(value) if isinstance(value, str) and value else None


@dataclass(frozen=True, kw_only=True)
class MemolumenSensorDescription(SensorEntityDescription):
    value: Callable[[dict[str, Any]], Any]


SENSORS = (
    MemolumenSensorDescription(
        key="lux", device_class=SensorDeviceClass.ILLUMINANCE, native_unit_of_measurement=LIGHT_LUX,
        state_class=SensorStateClass.MEASUREMENT, value=lambda d: d.get("lux"),
    ),
    MemolumenSensorDescription(
        key="photos", icon="mdi:image-multiple", state_class=SensorStateClass.MEASUREMENT,
        value=lambda d: d.get("photos"),
    ),
    MemolumenSensorDescription(
        key="next_on", device_class=SensorDeviceClass.TIMESTAMP, icon="mdi:monitor-shimmer",
        value=lambda d: _ts(d.get("nextOn")),
    ),
    MemolumenSensorDescription(
        key="version", icon="mdi:information-outline", entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda d: d.get("version"),
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: MemolumenConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(MemolumenSensor(coordinator, d) for d in SENSORS)


class MemolumenSensor(MemolumenEntity, SensorEntity):
    entity_description: MemolumenSensorDescription

    def __init__(self, coordinator, description: MemolumenSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return self.entity_description.value(self.coordinator.data)
