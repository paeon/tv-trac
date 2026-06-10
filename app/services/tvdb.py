"""
TheTVDB API v4 client.

Handles authentication and fetching show/season/episode metadata.
API docs: https://thetvdb.github.io/v4-api/
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api4.thetvdb.com/v4"


class TVDBClient:
    """Async client for TheTVDB v4 API."""

    def __init__(self) -> None:
        self._token: str | None = None
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=httpx.Timeout(10.0, connect=5.0),
            )
        return self._client

    async def authenticate(self) -> None:
        """Obtain a JWT bearer token from TheTVDB."""
        client = await self._get_client()
        body: dict[str, str] = {"apikey": settings.tvdb_api_key}
        if settings.tvdb_pin:
            body["pin"] = settings.tvdb_pin
        resp = await client.post("/login", json=body)
        resp.raise_for_status()
        data = resp.json()
        self._token = data["data"]["token"]
        logger.info("Authenticated with TheTVDB")

    async def _headers(self) -> dict[str, str]:
        if not self._token:
            await self.authenticate()
        return {"Authorization": f"Bearer {self._token}"}

    # ── Shows ────────────────────────────────────────────────────────────────

    async def search_show(self, name: str) -> list[dict[str, Any]]:
        """Search for a show by name. Returns list of matching shows."""
        client = await self._get_client()
        resp = await client.get(
            "/search",
            params={"query": name, "type": "series"},
            headers=await self._headers(),
        )
        resp.raise_for_status()
        return resp.json()["data"]  # list of series search results

    async def get_show(self, tvdb_id: int) -> dict[str, Any]:
        """Get full show record by TVDB ID."""
        client = await self._get_client()
        resp = await client.get(f"/series/{tvdb_id}", headers=await self._headers())
        resp.raise_for_status()
        return resp.json()["data"]

    async def get_show_extended(self, tvdb_id: int) -> dict[str, Any]:
        """Get extended show record (includes seasons + episodes)."""
        client = await self._get_client()
        resp = await client.get(
            f"/series/{tvdb_id}/extended", headers=await self._headers()
        )
        resp.raise_for_status()
        return resp.json()["data"]

    # ── Seasons ──────────────────────────────────────────────────────────────

    async def get_seasons(self, tvdb_id: int, page: int = 0) -> list[dict[str, Any]]:
        """Get all season type records for a series."""
        client = await self._get_client()
        resp = await client.get(
            f"/series/{tvdb_id}/episodes/default?page={page}",
            params={"season": 0},  # season=0 returns all seasons' episodes
            headers=await self._headers(),
        )
        resp.raise_for_status()
        return resp.json()["data"]

    # ── Episodes ─────────────────────────────────────────────────────────────

    async def get_episodes(
        self, series_id: int, season_type: str = "default", page: int = 0
    ) -> dict[str, Any]:
        """Get episodes for a series filtered by season type."""
        client = await self._get_client()
        resp = await client.get(
            f"/series/{series_id}/episodes/{season_type}/{page}",
            headers=await self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def get_season_extended(self, season_id: int) -> dict[str, Any]:
        """Get extended season record (includes episodes with full details)."""
        client = await self._get_client()
        resp = await client.get(
            f"/seasons/{season_id}/extended", headers=await self._headers()
        )
        resp.raise_for_status()
        return resp.json()["data"]

    async def get_episode_extended(self, episode_id: int) -> dict[str, Any]:
        """Get extended episode record with full details."""
        client = await self._get_client()
        resp = await client.get(
            f"/episodes/{episode_id}/extended", headers=await self._headers()
        )
        resp.raise_for_status()
        return resp.json()["data"]

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton convenience
tvdb = TVDBClient()
