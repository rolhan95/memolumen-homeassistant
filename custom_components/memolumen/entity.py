"""Gemeinsame Basis für alle Memolumen-Entitäten."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MemolumenCoordinator


class MemolumenEntity(CoordinatorEntity[MemolumenCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: MemolumenCoordinator, key: str) -> None:
        super().__init__(coordinator)
        device = coordinator.data.get("device") or {}
        device_id = device.get("id") or coordinator.config_entry.entry_id
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=f"Memolumen {device.get('name') or ''}".strip(),
            manufacturer="Suderland IT",
            model="Memolumen Bilderrahmen",
            sw_version=coordinator.data.get("version"),
            configuration_url=coordinator.api.url + "/admin/",
        )

    async def _refresh(self) -> None:
        await self.coordinator.async_request_refresh()
