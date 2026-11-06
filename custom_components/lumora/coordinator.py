"""Regelmäßige Abfrage des Lumora-Status."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LumoraApi, LumoraAuthError, LumoraError
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class LumoraCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Holt /api/ext/state und verteilt ihn an alle Entitäten."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: LumoraApi) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.state()
        except LumoraAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except LumoraError as err:
            raise UpdateFailed(str(err)) from err
