"""Einrichtung über die Oberfläche: Adresse des Rahmens und API-Token."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_TOKEN, CONF_URL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LumoraApi, LumoraAuthError, LumoraError
from .const import CONF_VERIFY_SSL, DOMAIN


def _normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if url.endswith("/admin"):
        url = url[: -len("/admin")]
    if "://" not in url:
        url = "https://" + url
    return url


class LumoraConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

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
