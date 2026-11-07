"""Zugriff auf die REST-Schnittstelle von Memolumen (/api/ext/…, Bearer-Token)."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp


class MemolumenError(Exception):
    """Allgemeiner Fehler beim Zugriff auf Memolumen."""


class MemolumenAuthError(MemolumenError):
    """API-Token fehlt oder ist falsch."""


class MemolumenApi:
    """Kleiner Client für die Memolumen-Steuerschnittstelle."""

    def __init__(self, session: aiohttp.ClientSession, url: str, token: str, verify_ssl: bool) -> None:
        self._session = session
        self._url = url.rstrip("/")
        self._token = token
        self._ssl = None if verify_ssl else False

    @property
    def url(self) -> str:
        return self._url

    async def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with asyncio.timeout(15):
                async with self._session.request(
                    method, f"{self._url}{path}", json=body, headers=headers, ssl=self._ssl
                ) as resp:
                    if resp.status == 401:
                        raise MemolumenAuthError("API-Token fehlt oder ist falsch")
                    data = await resp.json(content_type=None)
                    if resp.status >= 400:
                        raise MemolumenError((data or {}).get("error") or f"HTTP {resp.status}")
                    return data
        except MemolumenError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            detail = "Zeitüberschreitung (Tablet aus, im Standby oder Adresse falsch?)" if isinstance(err, asyncio.TimeoutError) else (str(err) or type(err).__name__)
            raise MemolumenError(f"Memolumen nicht erreichbar: {detail}") from err

    async def state(self) -> dict[str, Any]:
        return await self._request("GET", "/api/ext/state")

    async def set_display(self, on: bool, minutes: int | None = None) -> None:
        body: dict[str, Any] = {"on": on}
        if minutes:
            body["minutes"] = minutes
        await self._request("POST", "/api/ext/display", body)

    async def set_away(self, on: bool) -> None:
        await self._request("POST", "/api/ext/away", {"on": on})

    async def set_schedule(self, on: bool) -> None:
        await self._request("POST", "/api/ext/schedule", {"on": on})

    async def set_brightness(self, value: int) -> None:
        await self._request("POST", "/api/ext/brightness", {"value": value})

    async def command(self, name: str) -> None:
        await self._request("POST", f"/api/ext/command/{name}")

    async def notify(self, message: str, title: str = "", duration: int = 10) -> None:
        await self._request("POST", "/api/ext/notify", {"title": title, "message": message, "duration": duration})

    async def show_camera(self, entity: str, duration: int = 30, title: str = "", subtitle: str = "") -> None:
        await self._request(
            "POST", "/api/ext/camera", {"entity": entity, "duration": duration, "title": title, "subtitle": subtitle}
        )

    async def show_image(self, url: str, duration: int = 30, title: str = "", subtitle: str = "") -> None:
        await self._request(
            "POST", "/api/ext/image", {"url": url, "duration": duration, "title": title, "subtitle": subtitle}
        )

    async def motion(self) -> None:
        await self._request("POST", "/api/ext/motion", {})

    async def set_motion_source(self, enabled: bool, sensors: list[str]) -> None:
        await self._request("POST", "/api/ext/motion-source", {"enabled": enabled, "sensors": sensors})

    async def set_schedule_full(self, schedule: dict[str, Any]) -> None:
        """{on, entries?, nightMode} – Memolumen 3.0.0+"""
        await self._request("POST", "/api/ext/schedule", schedule)

    async def set_motion_settings(self, settings: dict[str, Any]) -> None:
        await self._request("POST", "/api/ext/motion-settings", settings)

    async def dismiss(self) -> None:
        await self._request("POST", "/api/ext/dismiss")
