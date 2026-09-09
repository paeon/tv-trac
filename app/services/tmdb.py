"""
TMDB (The Movie Database) API v3 client for movie metadata.

API docs: https://developer.themoviedb.org/reference
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


class TMDBClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._last_request = 0.0
        self._min_interval = 0.25  # ~4 req/sec, safely under TMDB's rate limit

    async def _rate_limit(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_request
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request = time.monotonic()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=httpx.Timeout(10.0, connect=5.0),
            )
        return self._client

    def _params(self, extra: dict | None = None) -> dict[str, Any]:
        p = {"api_key": settings.tmdb_api_key, "language": "en-US"}
        if extra:
            p.update(extra)
        return p

    async def search_movie(
        self, query: str, year: str | None = None
    ) -> list[dict[str, Any]]:
        """Search TMDB for a movie."""
        await self._rate_limit()
        client = await self._get_client()
        params: dict[str, Any] = {"query": query}
        if year:
            params["year"] = year
        resp = await client.get("/search/movie", params=self._params(params))
        resp.raise_for_status()
        return resp.json().get("results", [])

    async def get_movie(self, tmdb_id: int) -> dict[str, Any]:
        """Get full movie details."""
        await self._rate_limit()
        client = await self._get_client()
        resp = await client.get(f"/movie/{tmdb_id}", params=self._params())
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


tmdb = TMDBClient()
