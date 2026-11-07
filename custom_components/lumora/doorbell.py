"""Türklingel: Beim Auslösen eines gewählten Sensors blendet der Rahmen das Bild einer gewählten Kamera ein."""

from __future__ import annotations

import logging
import time

from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .api import LumoraApi, LumoraError
from .const import (
    CONF_DOORBELL_CAMERA,
    CONF_DOORBELL_COOLDOWN,
    CONF_DOORBELL_DURATION,
    CONF_DOORBELL_SUBTITLE,
    CONF_DOORBELL_TITLE,
    CONF_DOORBELL_TRIGGERS,
    DEFAULT_DOORBELL_COOLDOWN,
    DEFAULT_DOORBELL_DURATION,
    DEFAULT_DOORBELL_TITLE,
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


class Doorbell:
    """Beobachtet die Auslöser eines Lumora-Rahmens."""

    def __init__(self, hass: HomeAssistant, api: LumoraApi, options: dict) -> None:
        self.hass = hass
        self.api = api
        self.triggers: list[str] = list(options.get(CONF_DOORBELL_TRIGGERS) or [])
        self.camera: str | None = options.get(CONF_DOORBELL_CAMERA) or None
        self.duration = int(options.get(CONF_DOORBELL_DURATION, DEFAULT_DOORBELL_DURATION))
        self.title = options.get(CONF_DOORBELL_TITLE, DEFAULT_DOORBELL_TITLE) or ""
        self.subtitle = options.get(CONF_DOORBELL_SUBTITLE, "") or ""
        self.cooldown = int(options.get(CONF_DOORBELL_COOLDOWN, DEFAULT_DOORBELL_COOLDOWN))
        self._last = 0.0
        self.last_ring: float | None = None

    @property
    def configured(self) -> bool:
        return bool(self.camera)

    def start(self):
        """Listener anmelden; liefert die Abmeldefunktion (oder None)."""
        if not (self.triggers and self.camera):
            return None
        _LOGGER.debug("Lumora-Türklingel: %s → %s", self.triggers, self.camera)
        return async_track_state_change_event(self.hass, self.triggers, self._changed)

    @callback
    def _changed(self, event: Event[EventStateChangedData]) -> None:
        old, new = event.data.get("old_state"), event.data.get("new_state")
        if not is_ring(event.data["entity_id"], old.state if old else None, new.state if new else None):
            return
        now = time.monotonic()
        if now - self._last < self.cooldown:
            return
        self._last = now
        self.hass.async_create_task(self.ring(event.data["entity_id"]))

    async def ring(self, source: str = "test") -> None:
        """Kamerabild einblenden (auch für die Taste „Türklingel testen“)."""
        if not self.camera:
            return
        self.last_ring = time.time()
        try:
            await self.api.show_camera(self.camera, self.duration, self.title, self.subtitle)
            _LOGGER.info("Lumora: Türklingel (%s) – %s eingeblendet", source, self.camera)
        except LumoraError as err:
            _LOGGER.warning("Lumora: Kamera konnte nicht eingeblendet werden: %s", err)
