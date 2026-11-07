"""Nachricht als Banner auf dem Bilderrahmen anzeigen (notify.send_message)."""

from __future__ import annotations

from homeassistant.components.notify import NotifyEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MemolumenConfigEntry
from .entity import MemolumenEntity


async def async_setup_entry(hass: HomeAssistant, entry: MemolumenConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([MemolumenNotify(entry.runtime_data.coordinator, "message")])


class MemolumenNotify(MemolumenEntity, NotifyEntity):
    _attr_icon = "mdi:message-badge"

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        await self.coordinator.api.notify(message, title or "")
