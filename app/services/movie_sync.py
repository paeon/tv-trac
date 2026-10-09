"""
Movie scan → TMDB enrichment → Database persistence.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie
from app.services.images import download_image, store_local_image
from app.services.movie_scanner import scan_movie_root
from app.services.nfo import find_nfo
from app.services.tmdb import IMAGE_BASE, tmdb

logger = logging.getLogger(__name__)


async def sync_movies(db: AsyncSession) -> dict[str, Any]:
    scanned = scan_movie_root()
    if not scanned:
        return {"status": "empty", "message": "No movies found", "movies": []}

    results = []
    for sm in scanned:
        logger.info("Syncing movie %r", sm.title)
        try:
            r = await _sync_one_movie(db, sm)
            results.append(r)
        except Exception as exc:
            logger.exception("Failed to sync movie %r: %s", sm.title, exc)
            results.append({"title": sm.title, "status": "error", "error": str(exc)})

    # Soft-delete movies no longer on disk (match by id, robust to title changes)
    seen_ids = {r["movie_id"] for r in results if r.get("movie_id")}
    all_movies = await db.execute(select(Movie).where(Movie.deleted == False))  # noqa: E712
    deleted_count = 0
    for m in all_movies.scalars().all():
        if m.id not in seen_ids:
            m.deleted = True
            deleted_count += 1
    if deleted_count:
        await db.commit()

    created = sum(1 for r in results if r.get("status") == "created")
    updated = sum(1 for r in results if r.get("status") == "updated")
    skipped = sum(1 for r in results if r.get("status") == "skipped")
    return {
        "status": "ok",
        "movies_synced": len(results),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "deleted": deleted_count,
        "movies": results,
    }


def _extract_year(title: str) -> str | None:
    """Extract a year like (2023) from a folder name."""
    m = re.search(r"\((\d{4})\)", title)
    return m.group(1) if m else None


async def _sync_one_movie(db: AsyncSession, sm) -> dict[str, Any]:
    tmdb_id: int | None = None
    overview: str | None = None
    poster: str | None = None
    first_aired: str | None = None
    runtime: int | None = None
    imdb_id: str | None = None

    # Skip the API if this movie is already enriched.
    conditions = [Movie.title == sm.title]
    if sm.tmdb_id:
        conditions.append(Movie.tmdb_id == sm.tmdb_id)
    existing = await db.execute(select(Movie).where(or_(*conditions)))
    existing_movie = existing.scalar_one_or_none()
    if existing_movie and existing_movie.overview and existing_movie.first_aired:
        if existing_movie.deleted:
            existing_movie.deleted = False
            await db.commit()
        return {
            "title": sm.title,
            "movie_id": existing_movie.id,
            "status": "skipped",
        }

    # Try TMDB search
    try:
        # If .nfo provided a TMDB ID, use it directly
        if sm.tmdb_id:
            tmdb_id = sm.tmdb_id
            details = await tmdb.get_movie(tmdb_id)
            overview = details.get("overview")
            runtime = details.get("runtime")
            pp = details.get("poster_path")
            if pp:
                poster = IMAGE_BASE + pp
            first_aired = details.get("release_date")
            imdb_id = details.get("imdb_id")
            # Use .nfo title if available
            if sm.nfo_title:
                sm.title = sm.nfo_title
        else:
            title = re.sub(r"\s*\(\d{4}\)\s*$", "", sm.title).strip()
            year = _extract_year(sm.title) or sm.nfo_year
            results = await tmdb.search_movie(title, year)
            if results:
                best = results[0]
                tmdb_id = best.get("id")
                overview = best.get("overview")
                poster_path = best.get("poster_path")
                poster = IMAGE_BASE + poster_path if poster_path else None
                first_aired = best.get("release_date")

                if tmdb_id:
                    details = await tmdb.get_movie(tmdb_id)
                    overview = overview or details.get("overview")
                    runtime = details.get("runtime")
                    imdb_id = details.get("imdb_id")
                    if not poster:
                        pp = details.get("poster_path")
                        if pp:
                            poster = IMAGE_BASE + pp
                    first_aired = first_aired or details.get("release_date")
    except Exception:
        logger.warning("TMDB lookup failed for %r", sm.title)

    # Upsert
    conditions = [Movie.title == sm.title]
    if tmdb_id:
        conditions.append(Movie.tmdb_id == tmdb_id)
    result = await db.execute(select(Movie).where(or_(*conditions)))
    movie = result.scalar_one_or_none()

    is_new = movie is None
    if is_new:
        movie = Movie(
            title=sm.title,
            tmdb_id=tmdb_id,
            overview=overview,
            first_aired=first_aired,
            runtime=runtime,
            imdb_id=imdb_id,
            file_path=sm.file_path,
        )
        db.add(movie)
        await db.flush()
    else:
        if movie.deleted:
            movie.deleted = False
        if tmdb_id and not movie.tmdb_id:
            movie.tmdb_id = tmdb_id
        if overview and not movie.overview:
            movie.overview = overview
        if first_aired and not movie.first_aired:
            movie.first_aired = first_aired
        if runtime and not movie.runtime:
            movie.runtime = runtime
        if imdb_id and not movie.imdb_id:
            movie.imdb_id = imdb_id
        if not movie.file_path and sm.file_path:
            movie.file_path = sm.file_path

    # Prefer local artwork, then fall back to the TMDB poster
    if sm.poster_path:
        local_poster = store_local_image(sm.poster_path, "movie", movie.id)
        if local_poster:
            movie.poster_path = local_poster
    elif poster and (
        not movie.poster_path or movie.poster_path.startswith(("http://", "https://"))
    ):
        local_poster = await download_image(poster, "movie", movie.id)
        if local_poster:
            movie.poster_path = local_poster
        elif not movie.poster_path:
            movie.poster_path = poster

    await db.commit()

    return {
        "title": sm.title,
        "movie_id": movie.id,
        "tmdb_id": tmdb_id,
        "status": "created" if is_new else "updated",
    }
