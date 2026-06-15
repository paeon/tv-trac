"""
Local filesystem scanner.

Walks MEDIA_ROOT looking for a conventional TV folder layout:

    /media/tv/
      Show Name/
        Season 01/
          Show Name - S01E01 - Episode Title.mkv
          Show Name - S01E02 - Episode Title.mkv
        Season 02/
          ...

Parses filenames to extract season and episode numbers.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.services.nfo import find_nfo

logger = logging.getLogger(__name__)

# Common patterns: "S01E01", "s01e01", "1x01", "Season 1 Episode 01"
EPISODE_PATTERNS = [
    re.compile(r"[Ss](\d{1,4})[Ee](\d{1,4})"),  # S01E01
    re.compile(r"(\d{1,2})x(\d{1,4})"),  # 1x01
    re.compile(r"Season\s*(\d{1,4})\s*Episode\s*(\d{1,4})", re.IGNORECASE),
]

SEASON_DIR_PATTERN = re.compile(r"[Ss]eason\s*(\d{1,4})", re.IGNORECASE)

# Only count these extensions as episode files
VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".m4v", ".mov", ".wmv", ".flv", ".webm"}


@dataclass
class ScannedEpisode:
    file_path: str
    season_number: int
    episode_number: int
    filename: str


@dataclass
class ScannedSeason:
    season_number: int
    episodes: list[ScannedEpisode] = field(default_factory=list)


@dataclass
class ScannedShow:
    title: str
    folder_path: str
    tvdb_id: int | None = None
    tmdb_id: int | None = None
    seasons: dict[int, ScannedSeason] = field(default_factory=dict)


def _parse_episode(filename: str) -> tuple[int, int] | None:
    """Try to extract (season, episode) from a filename. Returns None on failure."""
    for pattern in EPISODE_PATTERNS:
        m = pattern.search(filename)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


def _parse_season_dir(dirname: str) -> int | None:
    """Try to extract season number from a directory name like 'Season 01'."""
    m = SEASON_DIR_PATTERN.search(dirname)
    if m:
        return int(m.group(1))
    return None


def scan_media_root() -> dict[str, ScannedShow]:
    """
    Walk the media root and build a dict of show-title -> ScannedShow.

    Expected layout:

        MEDIA_ROOT/
          Show Name/
            Season 01/
              episode files...
            Season 02/
              ...

    Returns an empty dict if MEDIA_ROOT doesn't exist or is unreadable.
    """
    root = Path(settings.media_root)
    if not root.exists() or not root.is_dir():
        logger.warning("Media root %s does not exist or is not a directory", root)
        return {}

    shows: dict[str, ScannedShow] = {}

    for show_dir in sorted(root.iterdir()):
        if not show_dir.is_dir():
            continue

        show = ScannedShow(title=show_dir.name, folder_path=str(show_dir))

        # Check for .nfo file for better title/ID matching
        nfo = find_nfo(Path(show_dir))
        if nfo:
            if nfo.title:
                show.title = nfo.title
            if nfo.tvdb_id:
                show.tvdb_id = nfo.tvdb_id
            if nfo.tmdb_id:
                show.tmdb_id = nfo.tmdb_id

        for season_dir in sorted(show_dir.iterdir()):
            if not season_dir.is_dir():
                continue

            season_num = _parse_season_dir(season_dir.name)
            if season_num is None:
                # Also check for bare episode files in the show dir itself
                continue

            season = ScannedSeason(season_number=season_num)
            show.seasons[season_num] = season

            for episode_file in sorted(season_dir.iterdir()):
                if not episode_file.is_file():
                    continue
                if episode_file.suffix.lower() not in VIDEO_EXTENSIONS:
                    continue  # skip non-video files (jpgs, nfos, etc.)
                parsed = _parse_episode(episode_file.name)
                if parsed is None:
                    continue  # not a recognized episode filename
                ep_season, ep_num = parsed
                if ep_season != season_num:
                    # File might be mis-placed; still include it under the dir's season
                    pass
                season.episodes.append(
                    ScannedEpisode(
                        file_path=str(episode_file),
                        season_number=ep_season,
                        episode_number=ep_num,
                        filename=episode_file.name,
                    )
                )

        # Only include shows that have at least one season with episodes
        if show.seasons:
            shows[show.title] = show

    logger.info("Scanned %d shows from %s", len(shows), root)
    return shows
