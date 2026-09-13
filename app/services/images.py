"""
Local image cache for posters and screenshots.

Artwork can come from two sources, tried in this order:

1. **Local media files** — posters/thumbnails already sitting next to the video
   files (Kodi/Plex/Emby conventions), copied into the cache.
2. **TheTVDB / TMDB** — downloaded via the API.

Both end up as a local `/images/...` URL so the UI never hot-links remote artwork.
"""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

IMAGE_DIR = Path(settings.image_dir).resolve()

# Recognize common image extensions in a URL (optionally followed by a query string).
_EXT_RE = re.compile(r"\.(jpe?g|png|webp|gif|bmp|svg)(?:\?|$)", re.IGNORECASE)

# Extensions we treat as local artwork (".tbn" is a Kodi JPEG thumbnail).
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tbn"}

# Common local poster/cover filenames, checked in priority order.
POSTER_FILENAMES = [
    "poster.jpg",
    "poster.png",
    "poster.webp",
    "poster.tbn",
    "folder.jpg",
    "folder.png",
    "folder.tbn",
    "show.jpg",
    "show.png",
    "movie.jpg",
    "movie.png",
    "cover.jpg",
    "cover.png",
]


def _local_url(kind: str, key: int | str, ext: str) -> str:
    return f"/images/{kind}/{key}{ext}"


def find_local_poster(directory: str | Path) -> str | None:
    """Find a local poster/cover image in a directory (Kodi/Plex/Emby conventions)."""
    d = Path(directory)
    if not d.is_dir():
        return None

    files = {p.name.lower(): p for p in d.iterdir() if p.is_file()}
    for name in POSTER_FILENAMES:
        p = files.get(name.lower())
        if p:
            return str(p)

    # Fallback: any file matching a poster/cover glob.
    for pat in ("*poster*", "*folder*", "*cover*"):
        for p in sorted(d.glob(pat)):
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                return str(p)
    return None


def find_local_thumbnail(video_file: str | Path) -> str | None:
    """Find a local screenshot/thumbnail next to a video file.

    Looks for an image with the same stem (e.g. ``Show - S01E01 - Title.jpg``)
    or a ``-thumb`` variant.
    """
    v = Path(video_file)
    stem = v.stem

    for ext in (".jpg", ".jpeg", ".png", ".webp", ".tbn"):
        candidate = v.with_suffix(ext)
        if candidate.is_file():
            return str(candidate)

    for ext in (".jpg", ".jpeg", ".png", ".webp", ".tbn"):
        candidate = v.with_name(stem + "-thumb" + ext)
        if candidate.is_file():
            return str(candidate)

    return None


def store_local_image(source: str, kind: str, key: int | str) -> str | None:
    """Copy a local image into the image cache and return its `/images/...` URL."""
    src = Path(source)
    if not src.is_file():
        return None

    ext = src.suffix.lower()
    ext_map = {".jpeg": ".jpg", ".tbn": ".jpg"}
    ext = ext_map.get(ext, ext)
    if ext not in (".jpg", ".png", ".webp", ".gif", ".bmp"):
        ext = ".jpg"

    dest_dir = IMAGE_DIR / kind
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{key}{ext}"

    try:
        shutil.copyfile(src, dest)
        return _local_url(kind, key, ext)
    except OSError as exc:
        logger.warning("Failed to copy local image %s: %s", src, exc)
        return None


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
