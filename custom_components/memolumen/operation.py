"""Betrieb & Zeitplan: Formularbereich der Optionen, Vorbelegung aus Memolumen und Übertragung an den Rahmen."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.helpers import selector

SECTION = "operation"

MODE = "mode"
MODE_SCHEDULE = "schedule"
MODE_ALWAYS = "always"
MODE_MOTION = "motion"

IDLE_OFF = "idle_off_minutes"
IDLE_MODE = "idle_mode"
WAKE_AT_NIGHT = "wake_at_night"
WAKE_DURATION = "wake_duration_minutes"
NIGHT_MODE = "night_mode"
BLOCKS = 3

# Wochentage wie in Memolumen: 0 = Sonntag … 6 = Samstag; Reihenfolge im Formular Mo–So
WEEKDAYS = ["1", "2", "3", "4", "5", "6", "0"]


def _days(n: int) -> str:
    return f"block{n}_days"


def _on(n: int) -> str:
    return f"block{n}_on"


def _off(n: int) -> str:
    return f"block{n}_off"


def supported(state: dict[str, Any] | None) -> bool:
    """Kann der Rahmen Zeitplan und Bewegungsregeln über die Schnittstelle setzen (Memolumen 3.0.0+)?"""
    return bool(state) and isinstance(state.get("schedule"), dict) and isinstance(state.get("motionSettings"), dict)


def defaults(state: dict[str, Any]) -> dict[str, Any]:
    """Formularwerte aus dem aktuellen Stand des Rahmens."""
    sched = state.get("schedule") or {}
    mot = state.get("motionSettings") or {}
    idle = int(mot.get("idleOffMinutes") or 0)
    if sched.get("enabled"):
        mode = MODE_SCHEDULE
    else:
        mode = MODE_MOTION if idle > 0 else MODE_ALWAYS
    values: dict[str, Any] = {
        MODE: mode,
        IDLE_OFF: idle if idle > 0 else 30,
        IDLE_MODE: mot.get("idleMode") or "blackout",
        WAKE_AT_NIGHT: bool(mot.get("wakeAtNight", True)),
        WAKE_DURATION: int(mot.get("wakeDurationMinutes") or 5),
        NIGHT_MODE: sched.get("nightMode") or "blackout",
    }
    entries = sched.get("entries") or []
    for n in range(1, BLOCKS + 1):
        e = entries[n - 1] if len(entries) >= n else None
        values[_days(n)] = [str(d) for d in (e or {}).get("days", [])]
        values[_on(n)] = f"{(e or {}).get('on', '07:00')}:00"
        values[_off(n)] = f"{(e or {}).get('off', '22:00')}:00"
    return values


def schema() -> vol.Schema:
    fields: dict[Any, Any] = {
        vol.Required(MODE): selector.SelectSelector(selector.SelectSelectorConfig(
            options=[MODE_SCHEDULE, MODE_ALWAYS, MODE_MOTION], translation_key="mode", mode=selector.SelectSelectorMode.LIST)),
        vol.Required(IDLE_OFF): selector.NumberSelector(selector.NumberSelectorConfig(
            min=0, max=600, step=1, unit_of_measurement="min", mode=selector.NumberSelectorMode.BOX)),
        vol.Required(IDLE_MODE): selector.SelectSelector(selector.SelectSelectorConfig(
            options=["blackout", "monitor-off"], translation_key="idle_mode", mode=selector.SelectSelectorMode.DROPDOWN)),
        vol.Required(WAKE_AT_NIGHT): selector.BooleanSelector(),
        vol.Required(WAKE_DURATION): selector.NumberSelector(selector.NumberSelectorConfig(
            min=1, max=240, step=1, unit_of_measurement="min", mode=selector.NumberSelectorMode.BOX)),
        vol.Required(NIGHT_MODE): selector.SelectSelector(selector.SelectSelectorConfig(
            options=["blackout", "monitor-off", "sleep", "hibernate"], translation_key="night_mode", mode=selector.SelectSelectorMode.DROPDOWN)),
    }
    for n in range(1, BLOCKS + 1):
        fields[vol.Optional(_days(n))] = selector.SelectSelector(selector.SelectSelectorConfig(
            options=WEEKDAYS, multiple=True, translation_key="weekday", mode=selector.SelectSelectorMode.DROPDOWN))
        fields[vol.Optional(_on(n))] = selector.TimeSelector()
        fields[vol.Optional(_off(n))] = selector.TimeSelector()
    return vol.Schema(fields)


def to_memolumen(values: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str | None]:
    """Formularwerte → (Zeitplan, Bewegungsregeln, Fehlerschlüssel)."""
    mode = values.get(MODE, MODE_SCHEDULE)
    entries = []
    for n in range(1, BLOCKS + 1):
        days = sorted({int(d) for d in values.get(_days(n)) or []})
        if not days:
            continue
        on, off = str(values.get(_on(n)) or "")[:5], str(values.get(_off(n)) or "")[:5]
        if not on or not off or on == off:
            return {}, {}, "schedule_block_invalid"
        entries.append({"days": days, "on": on, "off": off})
    if mode == MODE_SCHEDULE and not entries:
        return {}, {}, "schedule_empty"
    idle = int(values.get(IDLE_OFF) or 0)
    if mode == MODE_MOTION and idle < 1:
        return {}, {}, "idle_required"
    schedule: dict[str, Any] = {"on": mode == MODE_SCHEDULE, "nightMode": values.get(NIGHT_MODE, "blackout")}
    if entries:  # ohne Zeiträume (Immer an / Nur bei Bewegung) die im Rahmen gespeicherten behalten
        schedule["entries"] = entries
    motion = {
        # „Immer an“: nie wegen fehlender Bewegung ausschalten
        "idleOffMinutes": 0 if mode == MODE_ALWAYS else idle,
        "idleMode": values.get(IDLE_MODE, "blackout"),
        "wakeAtNight": bool(values.get(WAKE_AT_NIGHT, True)),
        "wakeDurationMinutes": int(values.get(WAKE_DURATION) or 5),
    }
    return schedule, motion, None
