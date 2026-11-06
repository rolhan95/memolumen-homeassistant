"""Schalter: Bildschirm, Abwesenheitsmodus, Zeitplan."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LumoraConfigEntry
from .api import LumoraApi
from .entity import LumoraEntity


@dataclass(frozen=True, kw_only=True)
class LumoraSwitchDescription(SwitchEntityDescription):
    value: Callable[[dict[str, Any]], bool]
    set_fn: Callable[[LumoraApi, bool], Awaitable[None]]


SWITCHES = (
    LumoraSwitchDescription(
        key="display", icon="mdi:monitor",
        value=lambda d: bool(d.get("displayOn")),
        set_fn=lambda api, on: api.set_display(on),
    ),
    LumoraSwitchDescription(
        key="away", icon="mdi:home-export-outline",
        value=lambda d: bool(d.get("away")),
        set_fn=lambda api, on: api.set_away(on),
    ),
    LumoraSwitchDescription(
        key="schedule", icon="mdi:calendar-clock", entity_category=EntityCategory.CONFIG,
        value=lambda d: bool(d.get("scheduleEnabled")),
        set_fn=lambda api, on: api.set_schedule(on),
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: LumoraConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(LumoraSwitch(coordinator, d) for d in SWITCHES)


class LumoraSwitch(LumoraEntity, SwitchEntity):
    entity_description: LumoraSwitchDescription

    def __init__(self, coordinator, description: LumoraSwitchDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return self.entity_description.value(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.entity_description.set_fn(self.coordinator.api, True)
        await self._refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.entity_description.set_fn(self.coordinator.api, False)
        await self._refresh()
