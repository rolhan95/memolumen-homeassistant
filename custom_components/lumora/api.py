"""Zugriff auf die REST-Schnittstelle von Lumora (/api/ext/…, Bearer-Token)."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp


class LumoraError(Exception):
    """Allgemeiner Fehler beim Zugriff auf Lumora."""


class LumoraAuthError(LumoraError):
    """API-Token fehlt oder ist falsch."""


class LumoraApi:
    """Kleiner Client für die Lumora-Steuerschnittstelle."""

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
                        raise LumoraAuthError("API-Token fehlt oder ist falsch")
                    data = await resp.json(content_type=None)
                    if resp.status >= 400:
                        raise LumoraError((data or {}).get("error") or f"HTTP {resp.status}")
                    return data
        except LumoraError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            raise LumoraError(f"Lumora nicht erreichbar: {err}") from err

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

    async def dismiss(self) -> None:
        await self._request("POST", "/api/ext/dismiss")
