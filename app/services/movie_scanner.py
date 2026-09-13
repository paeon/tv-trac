"""
Local filesystem scanner for movies.

Expected layout:

    MEDIA_ROOT_MOVIES/
      Inception (2010)/
        Inception (2010).mkv
      The Matrix (1999)/
        The Matrix (1999).mp4
      Some Movie/
        Some Movie.mkv

Parses folder names for movie titles. The year in parentheses is optional.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.services.images import find_local_poster
from app.services.nfo import find_nfo

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".m4v", ".mov", ".wmv", ".flv", ".webm"}


@dataclass
class ScannedMovie:
    title: str
    folder_path: str
    file_path: str | None = None
    filename: str | None = None
    tmdb_id: int | None = None
    tvdb_id: int | None = None
    nfo_title: str | None = None
    nfo_year: str | None = None
    poster_path: str | None = None


def scan_movie_root() -> list[ScannedMovie]:
    """
    Walk the movie media root and return a list of discovered movies.
    Returns empty list if the path doesn't exist.
    """
    root = Path(settings.media_root_movies)
    if not root.exists() or not root.is_dir():
        logger.warning("Movie root %s does not exist or is not a directory", root)
        return []

    movies: list[ScannedMovie] = []

    for movie_dir in sorted(root.iterdir()):
        if not movie_dir.is_dir():
            continue

        movie = ScannedMovie(title=movie_dir.name, folder_path=str(movie_dir))

        # Check for local poster artwork
        movie.poster_path = find_local_poster(movie_dir)

        # Check for .nfo file
        nfo = find_nfo(Path(movie_dir))
        if nfo:
            if nfo.title:
                movie.nfo_title = nfo.title
            if nfo.year:
                movie.nfo_year = nfo.year
            if nfo.tmdb_id:
                movie.tmdb_id = nfo.tmdb_id
            if nfo.tvdb_id:
                movie.tvdb_id = nfo.tvdb_id

        # Find the first video file
        for f in sorted(movie_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS:
                movie.file_path = str(f)
                movie.filename = f.name
                break

        # Include even if no video file found (might be empty or non-video)
        movies.append(movie)

    logger.info("Scanned %d movies from %s", len(movies), root)
    return movies
