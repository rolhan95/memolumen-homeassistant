"""Türklingel: Beim Auslösen eines gewählten Sensors oder eines Webhooks (z. B. vom Shelly)
blendet der Rahmen das Bild einer gewählten Kamera ein."""

from __future__ import annotations

import logging
import time

from homeassistant.components import webhook
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .api import LumoraApi, LumoraError
from .const import (
    CONF_DOORBELL_CAMERA,
    CONF_DOORBELL_COOLDOWN,
    CONF_DOORBELL_DURATION,
    CONF_DOORBELL_SUBTITLE,
    CONF_DOORBELL_TITLE,
    CONF_DOORBELL_TRIGGERS,
    CONF_DOORBELL_WEBHOOK,
    CONF_DOORBELL_WEBHOOK_ID,
    DEFAULT_DOORBELL_COOLDOWN,
    DEFAULT_DOORBELL_DURATION,
    DEFAULT_DOORBELL_TITLE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Diese Bereiche melden einen Druck durch einen neuen Zeitstempel als Zustand (nicht durch „an“)
TIMESTAMP_DOMAINS = ("event", "button", "input_button")


def is_ring(entity_id: str, old: str | None, new: str | None) -> bool:
    """Ist dieser Zustandswechsel ein Klingeln?"""
    # Start von Home Assistant (old None) oder Gerät wieder erreichbar (old „nicht verfügbar“) – kein Klingeln
    if new in (None, STATE_UNAVAILABLE, STATE_UNKNOWN) or old in (None, STATE_UNAVAILABLE):
        return False
    if entity_id.split(".")[0] in TIMESTAMP_DOMAINS:
        return new != old  # auch der allererste Druck (vorher „unbekannt“) zählt
    if old == STATE_UNKNOWN:
        return False
    return new == STATE_ON and old != STATE_ON


def webhook_url(hass: HomeAssistant, webhook_id: str) -> str:
    """Adresse für den Shelly – bevorzugt die lokale Adresse von Home Assistant."""
    try:
        base = get_url(hass, allow_external=False)
    except NoURLAvailableError:
        try:
            base = get_url(hass)
        except NoURLAvailableError:
            base = "http://<Adresse von Home Assistant>:8123"
    return f"{base.rstrip('/')}/api/webhook/{webhook_id}"


def webhook_in_use(hass: HomeAssistant, webhook_id: str, own_id: str | None) -> bool:
    """Ist die Webhook-ID schon von etwas anderem belegt (z. B. einer Automation)?"""
    handlers = hass.data.get("webhook") or {}
    return webhook_id in handlers and webhook_id != own_id


class Doorbell:
    """Beobachtet die Auslöser eines Lumora-Rahmens."""

    def __init__(self, hass: HomeAssistant, api: LumoraApi, options: dict, name: str = "Lumora") -> None:
        self.hass = hass
        self.api = api
        self.name = name
        self.triggers: list[str] = list(options.get(CONF_DOORBELL_TRIGGERS) or [])
        self.camera: str | None = options.get(CONF_DOORBELL_CAMERA) or None
        self.duration = int(options.get(CONF_DOORBELL_DURATION, DEFAULT_DOORBELL_DURATION))
        self.title = options.get(CONF_DOORBELL_TITLE, DEFAULT_DOORBELL_TITLE) or ""
        self.subtitle = options.get(CONF_DOORBELL_SUBTITLE, "") or ""
        self.cooldown = int(options.get(CONF_DOORBELL_COOLDOWN, DEFAULT_DOORBELL_COOLDOWN))
        self.webhook_id: str | None = (options.get(CONF_DOORBELL_WEBHOOK_ID) or None) if options.get(CONF_DOORBELL_WEBHOOK) else None
        self._last = 0.0
        self.last_ring: float | None = None

    @property
    def configured(self) -> bool:
        return bool(self.camera)

    def start(self):
        """Listener und Webhook anmelden; liefert eine Abmeldefunktion (oder None)."""
        if not self.camera:
            return None
        unsubs = []
        if self.triggers:
            _LOGGER.debug("Lumora-Türklingel: %s → %s", self.triggers, self.camera)
            unsubs.append(async_track_state_change_event(self.hass, self.triggers, self._changed))
        if self.webhook_id:
            try:
                webhook.async_register(
                    self.hass, DOMAIN, f"{self.name} – Türklingel", self.webhook_id, self._webhook,
                    local_only=True, allowed_methods=("GET", "POST", "PUT"),
                )
                hook_id = self.webhook_id
                unsubs.append(lambda: webhook.async_unregister(self.hass, hook_id))
                _LOGGER.debug("Lumora-Türklingel: Webhook %s aktiv", hook_id)
            except ValueError:
                _LOGGER.error(
                    "Lumora: Webhook-ID %s ist schon belegt (z. B. von einer Automation) – Türklingel per Webhook inaktiv",
                    self.webhook_id,
                )
        if not unsubs:
            return None

        def unsub_all() -> None:
            for u in unsubs:
                u()
        return unsub_all

    @callback
    def _changed(self, event: Event[EventStateChangedData]) -> None:
        old, new = event.data.get("old_state"), event.data.get("new_state")
        if is_ring(event.data["entity_id"], old.state if old else None, new.state if new else None):
            self._trigger(event.data["entity_id"])

    async def _webhook(self, hass: HomeAssistant, webhook_id: str, request) -> None:
        # Der Shelly ruft die Adresse beim Drücken auf; Inhalt der Anfrage wird nicht ausgewertet
        self._trigger("Webhook")

    @callback
    def _trigger(self, source: str) -> None:
        now = time.monotonic()
        if now - self._last < self.cooldown:
            _LOGGER.debug("Lumora-Türklingel: %s innerhalb der Sperrzeit ignoriert", source)
            return
        self._last = now
        self.hass.async_create_task(self.ring(source))

    async def ring(self, source: str = "Test") -> None:
        """Kamerabild einblenden (auch für die Taste „Türklingel testen“)."""
        if not self.camera:
            return
        self.last_ring = time.time()
        try:
            await self.api.show_camera(self.camera, self.duration, self.title, self.subtitle)
            _LOGGER.info("Lumora: Türklingel (%s) – %s eingeblendet", source, self.camera)
        except LumoraError as err:
            _LOGGER.warning("Lumora: Kamera konnte nicht eingeblendet werden: %s", err)
