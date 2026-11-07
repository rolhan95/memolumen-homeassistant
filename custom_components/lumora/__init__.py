"""Lumora – digitaler Bilderrahmen: Steuerung aus Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_TOKEN, CONF_URL, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import LumoraApi, LumoraError
from .const import (
    CONF_VERIFY_SSL,
    DOMAIN,
    SERVICE_DISMISS,
    SERVICE_DISPLAY_ON_FOR,
    SERVICE_NOTIFY,
    SERVICE_SHOW_CAMERA,
    SERVICE_SHOW_IMAGE,
)
from .coordinator import LumoraCoordinator
from .doorbell import Doorbell

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.NOTIFY, Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class LumoraData:
    api: LumoraApi
    coordinator: LumoraCoordinator
    doorbell: Doorbell


type LumoraConfigEntry = ConfigEntry[LumoraData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Aktionen (Dienste) einmalig registrieren."""
    _register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: LumoraConfigEntry) -> bool:
    session = async_get_clientsession(hass, verify_ssl=entry.data.get(CONF_VERIFY_SSL, False))
    api = LumoraApi(session, entry.data[CONF_URL], entry.data[CONF_TOKEN], entry.data.get(CONF_VERIFY_SSL, False))
    coordinator = LumoraCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    doorbell = Doorbell(hass, api, dict(entry.options))
    entry.runtime_data = LumoraData(api, coordinator, doorbell)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    unsub = doorbell.start()
    if unsub:
        entry.async_on_unload(unsub)
    # Geänderte Optionen (Türklingel) sofort übernehmen
    entry.async_on_unload(entry.add_update_listener(_options_updated))
    return True


async def _options_updated(hass: HomeAssistant, entry: LumoraConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: LumoraConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


# ---------- Aktionen ----------
ATTR_DEVICE_ID = "device_id"
ATTR_DURATION = "duration"
ATTR_TITLE = "title"
ATTR_SUBTITLE = "subtitle"
ATTR_MESSAGE = "message"
ATTR_URL = "url"
ATTR_CAMERA = "camera"
ATTR_MINUTES = "minutes"

_TARGET = {vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string])}
_OVERLAY = {
    vol.Optional(ATTR_DURATION, default=30): vol.All(vol.Coerce(int), vol.Range(min=3, max=600)),
    vol.Optional(ATTR_TITLE, default=""): cv.string,
    vol.Optional(ATTR_SUBTITLE, default=""): cv.string,
}


def _entries_for(hass: HomeAssistant, call: ServiceCall) -> list[LumoraConfigEntry]:
    """Ziel-Rahmen: gewählte Geräte, sonst alle eingerichteten Lumora-Rahmen."""
    loaded = [e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED]
    device_ids = call.data.get(ATTR_DEVICE_ID)
    if not device_ids:
        if not loaded:
            raise ServiceValidationError("Kein Lumora-Bilderrahmen eingerichtet")
        return loaded
    registry = dr.async_get(hass)
    result = []
    for device_id in device_ids:
        device = registry.async_get(device_id)
        entry = next((e for e in loaded if device and e.entry_id in device.config_entries), None)
        if entry is None:
            raise ServiceValidationError(f"Gerät {device_id} ist kein Lumora-Bilderrahmen")
        result.append(entry)
    return result


def _register_services(hass: HomeAssistant) -> None:
    async def run(call: ServiceCall, action) -> None:
        for entry in _entries_for(hass, call):
            try:
                await action(entry.runtime_data.api)
            except LumoraError as err:
                raise HomeAssistantError(f"Lumora: {err}") from err
            await entry.runtime_data.coordinator.async_request_refresh()

    async def show_camera(call: ServiceCall) -> None:
        d = call.data
        await run(call, lambda api: api.show_camera(d[ATTR_CAMERA], d[ATTR_DURATION], d[ATTR_TITLE], d[ATTR_SUBTITLE]))

    async def show_image(call: ServiceCall) -> None:
        d = call.data
        await run(call, lambda api: api.show_image(d[ATTR_URL], d[ATTR_DURATION], d[ATTR_TITLE], d[ATTR_SUBTITLE]))

    async def notify(call: ServiceCall) -> None:
        d = call.data
        await run(call, lambda api: api.notify(d[ATTR_MESSAGE], d.get(ATTR_TITLE, ""), d[ATTR_DURATION]))

    async def dismiss(call: ServiceCall) -> None:
        await run(call, lambda api: api.dismiss())

    async def display_on_for(call: ServiceCall) -> None:
        await run(call, lambda api: api.set_display(True, call.data[ATTR_MINUTES]))

    hass.services.async_register(
        DOMAIN, SERVICE_SHOW_CAMERA, show_camera,
        schema=vol.Schema({**_TARGET, vol.Required(ATTR_CAMERA): cv.entity_id, **_OVERLAY}),
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SHOW_IMAGE, show_image,
        schema=vol.Schema({**_TARGET, vol.Required(ATTR_URL): cv.string, **_OVERLAY}),
    )
    hass.services.async_register(
        DOMAIN, SERVICE_NOTIFY, notify,
        schema=vol.Schema({
            **_TARGET,
            vol.Required(ATTR_MESSAGE): cv.string,
            vol.Optional(ATTR_TITLE, default=""): cv.string,
            vol.Optional(ATTR_DURATION, default=10): vol.All(vol.Coerce(int), vol.Range(min=3, max=600)),
        }),
    )
    hass.services.async_register(DOMAIN, SERVICE_DISMISS, dismiss, schema=vol.Schema(_TARGET))
    hass.services.async_register(
        DOMAIN, SERVICE_DISPLAY_ON_FOR, display_on_for,
        schema=vol.Schema({**_TARGET, vol.Required(ATTR_MINUTES): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440))}),
    )
