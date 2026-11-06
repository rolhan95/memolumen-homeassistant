"""Nachricht als Banner auf dem Bilderrahmen anzeigen (notify.send_message)."""

from __future__ import annotations

from homeassistant.components.notify import NotifyEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LumoraConfigEntry
from .entity import LumoraEntity


async def async_setup_entry(hass: HomeAssistant, entry: LumoraConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([LumoraNotify(entry.runtime_data.coordinator, "message")])


class LumoraNotify(LumoraEntity, NotifyEntity):
    _attr_icon = "mdi:message-badge"

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        await self.coordinator.api.notify(message, title or "")
