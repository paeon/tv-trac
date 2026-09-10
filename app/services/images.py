"""
Local image cache for posters.

Posters are fetched from TheTVDB / TMDB during a scan, written to a local
directory, and stored in the database as a local `/images/...` URL so the UI
never has to hot-link remote artwork again.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

IMAGE_DIR = Path(settings.image_dir).resolve()

# Recognize common image extensions in a URL (optionally followed by a query string).
_EXT_RE = re.compile(r"\.(jpe?g|png|webp|gif|bmp|svg)(?:\?|$)", re.IGNORECASE)


def _local_url(kind: str, key: int | str, ext: str) -> str:
    return f"/images/{kind}/{key}{ext}"


async def download_image(url: str, kind: str, key: int | str) -> str | None:
    """Download a remote image and return a local `/images/...` URL.

    - Returns ``None`` when there is no URL or the download fails, so callers
      can fall back to the original remote URL.
    - Is idempotent: if the file already exists locally it is reused.
    - ``kind`` is a directory name (e.g. ``"show"`` / ``"movie"``) and ``key``
      is a stable identifier (the database row id).
    """
    if not url:
        return None
    if url.startswith("/images/"):
        return url

    ext = ".jpg"
    m = _EXT_RE.search(url)
    if m:
        ext = "." + m.group(1).lower()
        if ext == ".jpeg":
            ext = ".jpg"

    dest_dir = IMAGE_DIR / kind
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{key}{ext}"

    if dest.exists() and dest.stat().st_size > 0:
        return _local_url(kind, key, ext)

    tmp = dest.with_suffix(dest.suffix + ".tmp")
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0),
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.content
        if not data:
            return None
        tmp.write_bytes(data)
        tmp.replace(dest)
        return _local_url(kind, key, ext)
    except Exception:
        logger.warning("Failed to download poster %s", url)
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
        return None
