"""Bewegungsmelder im Raum: Bewegung aus Home Assistant an den Rahmen melden.
Lumora wendet darauf die Regeln aus „Bewegung“ an (nachts einschalten, Dauer, tagsüber ausschalten ohne Bewegung)."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.const import STATE_ON
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval

from .api import LumoraApi, LumoraError

_LOGGER = logging.getLogger(__name__)

# Präsenzmelder bleiben bei Anwesenheit „an“ – dann regelmäßig erneut melden
KEEPALIVE = timedelta(seconds=60)


class RoomMotion:
    def __init__(self, hass: HomeAssistant, api: LumoraApi, sensors: list[str]) -> None:
        self.hass = hass
        self.api = api
        self.sensors = list(sensors or [])
        self._warned = False

    def _names(self) -> list[str]:
        names = []
        for eid in self.sensors:
            st = self.hass.states.get(eid)
            names.append(st.name if st else eid)
        return names

    async def async_start(self):
        """Kopplung an Lumora melden und Listener anmelden; liefert eine Abmeldefunktion (oder None)."""
        try:
            await self.api.set_motion_source(bool(self.sensors), self._names())
        except LumoraError as err:
            if self.sensors:
                _LOGGER.warning("Lumora: Bewegungsmelder konnte nicht gekoppelt werden (Lumora 2.3.2 oder neuer nötig): %s", err)
            else:
                _LOGGER.debug("Lumora: Entkoppeln nicht möglich (ältere Lumora-Version?): %s", err)
            return None
        if not self.sensors:
            return None
        unsubs = [
            async_track_state_change_event(self.hass, self.sensors, self._changed),
            async_track_time_interval(self.hass, self._keepalive, KEEPALIVE),
        ]

        def unsub_all() -> None:
            for u in unsubs:
                u()
        return unsub_all

    @callback
    def _changed(self, event: Event[EventStateChangedData]) -> None:
        new = event.data.get("new_state")
        old = event.data.get("old_state")
        if new is not None and new.state == STATE_ON and (old is None or old.state != STATE_ON):
            self.hass.async_create_task(self._report(event.data["entity_id"]))

    async def _keepalive(self, _now) -> None:
        on = [e for e in self.sensors if (st := self.hass.states.get(e)) is not None and st.state == STATE_ON]
        if on:
            await self._report(on[0])

    async def _report(self, source: str) -> None:
        try:
            await self.api.motion()
            self._warned = False
            _LOGGER.debug("Lumora: Bewegung von %s gemeldet", source)
        except LumoraError as err:
            if not self._warned:
                _LOGGER.warning("Lumora: Bewegung konnte nicht gemeldet werden: %s", err)
                self._warned = True
