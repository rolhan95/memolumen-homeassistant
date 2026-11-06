"""Tasten: Foto vor/zurück, Pause/Weiter, Einblendung schließen, App neu starten."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LumoraConfigEntry
from .entity import LumoraEntity

# key → Befehl der Lumora-Schnittstelle (None = Einblendung schließen)
BUTTONS = (
    (ButtonEntityDescription(key="next", icon="mdi:skip-next"), "next"),
    (ButtonEntityDescription(key="prev", icon="mdi:skip-previous"), "prev"),
    (ButtonEntityDescription(key="pause", icon="mdi:pause"), "pause"),
    (ButtonEntityDescription(key="resume", icon="mdi:play"), "resume"),
    (ButtonEntityDescription(key="dismiss", icon="mdi:close-box"), None),
    (ButtonEntityDescription(key="restart", icon="mdi:restart", entity_category=EntityCategory.CONFIG), "restart-app"),
)


async def async_setup_entry(hass: HomeAssistant, entry: LumoraConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(LumoraButton(coordinator, d, cmd) for d, cmd in BUTTONS)


class LumoraButton(LumoraEntity, ButtonEntity):
    def __init__(self, coordinator, description: ButtonEntityDescription, command: str | None) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._command = command

    async def async_press(self) -> None:
        if self._command is None:
            await self.coordinator.api.dismiss()
        else:
            await self.coordinator.api.command(self._command)
