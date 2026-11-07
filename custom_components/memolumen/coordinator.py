"""Regelmäßige Abfrage des Memolumen-Status."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MemolumenApi, MemolumenAuthError, MemolumenError
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class MemolumenCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Holt /api/ext/state und verteilt ihn an alle Entitäten."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: MemolumenApi) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.state()
        except MemolumenAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except MemolumenError as err:
            raise UpdateFailed(str(err)) from err
