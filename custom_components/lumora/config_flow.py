"""Einrichtung über die Oberfläche: Adresse des Rahmens und API-Token."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_TOKEN, CONF_URL
from homeassistant.components import persistent_notification, webhook
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LumoraApi, LumoraAuthError, LumoraError
from .doorbell import webhook_in_use, webhook_url
from .const import (
    CONF_DOORBELL_CAMERA,
    CONF_DOORBELL_COOLDOWN,
    CONF_DOORBELL_DURATION,
    CONF_DOORBELL_SUBTITLE,
    CONF_DOORBELL_TITLE,
    CONF_DOORBELL_TRIGGERS,
    CONF_DOORBELL_WEBHOOK,
    CONF_DOORBELL_WEBHOOK_ID,
    CONF_MOTION_SENSORS,
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
    """Optionen: Türklingel – Auslöser (Entitäten und/oder Webhook) und Kamera für die Einblendung am Rahmen."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        current = dict(self.config_entry.options)
        own_hook = current.get(CONF_DOORBELL_WEBHOOK_ID) if current.get(CONF_DOORBELL_WEBHOOK) else None
        if user_input is not None:
            triggers = user_input.get(CONF_DOORBELL_TRIGGERS) or []
            camera = user_input.get(CONF_DOORBELL_CAMERA)
            use_hook = bool(user_input.get(CONF_DOORBELL_WEBHOOK))
            hook_id = (user_input.get(CONF_DOORBELL_WEBHOOK_ID) or "").strip()
            if use_hook and not hook_id:
                hook_id = webhook.async_generate_id()
            user_input[CONF_DOORBELL_WEBHOOK_ID] = hook_id
            if (triggers or use_hook) and not camera:
                errors[CONF_DOORBELL_CAMERA] = "camera_required"
            elif camera and not (triggers or use_hook):
                errors["base"] = "trigger_required"
            elif use_hook and not all(ch.isalnum() or ch in "-_" for ch in hook_id):
                errors[CONF_DOORBELL_WEBHOOK_ID] = "webhook_invalid"
            elif use_hook and webhook_in_use(self.hass, hook_id, own_hook):
                errors[CONF_DOORBELL_WEBHOOK_ID] = "webhook_in_use"
            else:
                if use_hook:
                    _notify_webhook(self.hass, hook_id)
                return self.async_create_entry(data=user_input)

        suggested = user_input or current
        if not suggested.get(CONF_DOORBELL_WEBHOOK_ID):
            suggested = {**suggested, CONF_DOORBELL_WEBHOOK_ID: webhook.async_generate_id()}
        # Eigene Entitäten (z. B. die Kamera-Bewegung des Rahmens) nicht anbieten – das ergäbe eine Rückkopplung
        own = [e.entity_id for e in er.async_entries_for_config_entry(er.async_get(self.hass), self.config_entry.entry_id)]
        schema = vol.Schema({
            vol.Optional(CONF_MOTION_SENSORS): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor", multiple=True, exclude_entities=own)
            ),
            vol.Optional(CONF_DOORBELL_TRIGGERS): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=DOORBELL_TRIGGER_DOMAINS, multiple=True)
            ),
            vol.Optional(CONF_DOORBELL_WEBHOOK, default=False): selector.BooleanSelector(),
            vol.Optional(CONF_DOORBELL_WEBHOOK_ID): selector.TextSelector(),
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
        hook_now = suggested.get(CONF_DOORBELL_WEBHOOK_ID) if suggested.get(CONF_DOORBELL_WEBHOOK) else None
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors,
            description_placeholders={"webhook_url": webhook_url(self.hass, hook_now) if hook_now else "–"},
        )


def _notify_webhook(hass, hook_id: str) -> None:
    """Shelly-Adresse als Benachrichtigung in Home Assistant anzeigen (bleibt, bis sie geschlossen wird)."""
    url = webhook_url(hass, hook_id)
    persistent_notification.async_create(
        hass,
        f"Adresse für den Shelly (Türklingel):\n\n`{url}`\n\n"
        "**Shelly Plus/Pro/Gen3/Gen4:** Weboberfläche → Actions → neue Aktion → Auslöser „Input toggled on“ "
        "bzw. „Button push“ → Webhook/URL aufrufen → Adresse einfügen.\n\n"
        "**Shelly Gen1:** Settings → I/O URL actions → „Button switched ON url“ bzw. „Button short press url“.\n\n"
        "Die Adresse funktioniert nur im Heimnetz.",
        title="Lumora: Türklingel per Webhook",
        notification_id=f"lumora_webhook_{hook_id}",
    )