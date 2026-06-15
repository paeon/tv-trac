"""
Parse Kodi/XBMC .nfo files for TV shows and movies.

Typical tvshow.nfo:
  <tvshow>
    <title>Breaking Bad</title>
    <uniqueid type="tvdb">81189</uniqueid>
    <year>2008</year>
  </tvshow>

Typical movie.nfo:
  <movie>
    <title>Inception</title>
    <uniqueid type="tmdb">27205</uniqueid>
    <year>2010</year>
  </movie>
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class NfoData:
    title: str | None = None
    year: str | None = None
    tvdb_id: int | None = None
    tmdb_id: int | None = None


def parse_nfo(filepath: Path) -> NfoData | None:
    """Parse a .nfo file and extract relevant metadata."""
    try:
        if not filepath.exists():
            return None
        tree = ET.parse(str(filepath))
        root = tree.getroot()

        data = NfoData()

        # Title
        data.title = _text(root, "title")

        # Year
        data.year = _text(root, "year") or _text(root, "premiered")

        # Unique IDs
        for uid in root.findall(".//uniqueid"):
            id_type = uid.get("type", "").lower()
            try:
                val = int(uid.text or "")
            except (ValueError, TypeError):
                continue
            if id_type == "tvdb":
                data.tvdb_id = val
            elif id_type == "tmdb":
                data.tmdb_id = val

        return data if (data.title or data.tvdb_id or data.tmdb_id) else None

    except ET.ParseError:
        logger.warning("Failed to parse .nfo: %s", filepath)
        return None
    except Exception:
        logger.exception("Error reading .nfo: %s", filepath)
        return None


def _text(element: Any, tag: str) -> str | None:
    """Get text content of a child element, or None."""
    child = element.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return None


def find_nfo(directory: Path, basename: str | None = None) -> NfoData | None:
    """
    Look for .nfo files in a directory. Checks:
      1. directory / tvshow.nfo
      2. directory / movie.nfo
      3. directory / {basename}.nfo (e.g. "Breaking Bad.nfo")
    Returns the first one that parses successfully.
    """
    candidates = []

    # Common names
    for name in ("tvshow.nfo", "movie.nfo"):
        p = directory / name
        if p.exists():
            candidates.append(p)

    # Basename match
    if basename:
        p = directory / f"{basename}.nfo"
        if p.exists():
            candidates.append(p)

    # Any other .nfo file in the directory
    for p in sorted(directory.glob("*.nfo")):
        if p not in candidates:
            candidates.append(p)

    for p in candidates:
        data = parse_nfo(p)
        if data:
            logger.info(
                "Parsed .nfo: %s → title=%r tvdb=%s tmdb=%s",
                p.name,
                data.title,
                data.tvdb_id,
                data.tmdb_id,
            )
            return data

    return None
