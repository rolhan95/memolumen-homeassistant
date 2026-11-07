"""Einrichtung über die Oberfläche: Adresse des Rahmens und API-Token."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_TOKEN, CONF_URL
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LumoraApi, LumoraAuthError, LumoraError
from .const import (
    CONF_DOORBELL_CAMERA,
    CONF_DOORBELL_COOLDOWN,
    CONF_DOORBELL_DURATION,
    CONF_DOORBELL_SUBTITLE,
    CONF_DOORBELL_TITLE,
    CONF_DOORBELL_TRIGGERS,
    CONF_VERIFY_SSL,
    DEFAULT_DOORBELL_COOLDOWN,
    DEFAULT_DOORBELL_DURATION,
    DEFAULT_DOORBELL_TITLE,
    DOMAIN,
    DOORBELL_TRIGGER_DOMAINS,
)


def _normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if url.endswith("/admin"):
        url = url[: -len("/admin")]
    if "://" not in url:
        url = "https://" + url
    return url


class LumoraConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return LumoraOptionsFlow()

    async def _validate(self, data: dict[str, Any]) -> dict[str, Any]:
        session = async_get_clientsession(self.hass, verify_ssl=data[CONF_VERIFY_SSL])
        api = LumoraApi(session, data[CONF_URL], data[CONF_TOKEN], data[CONF_VERIFY_SSL])
        return await api.state()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                CONF_URL: _normalize_url(user_input[CONF_URL]),
                CONF_TOKEN: user_input[CONF_TOKEN].strip(),
                CONF_VERIFY_SSL: user_input.get(CONF_VERIFY_SSL, False),
            }
            try:
                state = await self._validate(data)
            except LumoraAuthError:
                errors["base"] = "invalid_auth"
            except LumoraError:
                errors["base"] = "cannot_connect"
            else:
                device = state.get("device") or {}
                await self.async_set_unique_id(device.get("id") or data[CONF_URL])
                self._abort_if_unique_id_configured(updates=data)
                return self.async_create_entry(title=f"Lumora {device.get('name') or ''}".strip(), data=data)

        schema = vol.Schema({
            vol.Required(CONF_URL, default=(user_input or {}).get(CONF_URL, "https://")): str,
            vol.Required(CONF_TOKEN): str,
            vol.Optional(CONF_VERIFY_SSL, default=False): bool,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            data = {**entry.data, CONF_TOKEN: user_input[CONF_TOKEN].strip()}
            try:
                await self._validate(data)
            except LumoraAuthError:
                errors["base"] = "invalid_auth"
            except LumoraError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(entry, data=data)
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}), errors=errors
        )


class LumoraOptionsFlow(OptionsFlow):
    """Optionen: Türklingel – Auslöser und Kamera für die Einblendung am Rahmen."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            triggers = user_input.get(CONF_DOORBELL_TRIGGERS) or []
            camera = user_input.get(CONF_DOORBELL_CAMERA)
            if triggers and not camera:
                errors[CONF_DOORBELL_CAMERA] = "camera_required"
            elif camera and not triggers:
                errors[CONF_DOORBELL_TRIGGERS] = "trigger_required"
            else:
                return self.async_create_entry(data=user_input)

        schema = vol.Schema({
            vol.Optional(CONF_DOORBELL_TRIGGERS): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=DOORBELL_TRIGGER_DOMAINS, multiple=True)
            ),
            vol.Optional(CONF_DOORBELL_CAMERA): selector.EntitySelector(selector.EntitySelectorConfig(domain="camera")),
            vol.Optional(CONF_DOORBELL_DURATION, default=DEFAULT_DOORBELL_DURATION): selector.NumberSelector(
                selector.NumberSelectorConfig(min=5, max=600, step=5, unit_of_measurement="s", mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(CONF_DOORBELL_TITLE, default=DEFAULT_DOORBELL_TITLE): selector.TextSelector(),
            vol.Optional(CONF_DOORBELL_SUBTITLE): selector.TextSelector(),
            vol.Optional(CONF_DOORBELL_COOLDOWN, default=DEFAULT_DOORBELL_COOLDOWN): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=300, step=1, unit_of_measurement="s", mode=selector.NumberSelectorMode.BOX)
            ),
        })
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or dict(self.config_entry.options)),
            errors=errors,
        )