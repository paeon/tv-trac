"""
Scan → TVDB enrichment → Database persistence orchestrator.

Takes the output of the filesystem scanner, matches each show against
TheTVDB, fetches full metadata, and upserts everything into the database.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.show import Episode, Season, Show
from app.services.scanner import ScannedShow, scan_media_root
from app.services.tvdb import tvdb

logger = logging.getLogger(__name__)

# TheTVDB v4 returns IDs like "series-393268" — extract the numeric portion
_TVDB_ID_RE = re.compile(r"[a-z]+-(\d+)", re.IGNORECASE)


def _parse_tvdb_id(raw: Any) -> int | None:
    """Parse a TheTVDB ID which may be a string like 'series-393268' or a plain int."""
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        m = _TVDB_ID_RE.match(raw)
        if m:
            return int(m.group(1))
        try:
            return int(raw)
        except (ValueError, TypeError):
            pass
    return None


async def sync_shows(db: AsyncSession) -> dict[str, Any]:
    """
    Full scan-and-sync pipeline:

    1. Scan the local media directory
    2. For each show found, search TheTVDB and fetch metadata
    3. Upsert Show, Seasons, and Episodes into the database
    4. Mark episodes as watched if a local file exists

    Works offline: if TVDB is unreachable, shows are still created from local data.
    """
    scanned = scan_media_root()
    if not scanned:
        return {
            "status": "empty",
            "message": "No shows found in media root",
            "shows": [],
        }

    # Pre-flight check — if TVDB is down, skip it for all shows
    tvdb_available = False
    try:
        await tvdb.authenticate()
        tvdb_available = True
    except Exception:
        logger.warning("TVDB is unreachable — proceeding with local data only")

    results = []
    for title, scanned_show in sorted(scanned.items()):
        try:
            show_result = await _sync_one_show(db, title, scanned_show, tvdb_available)
            results.append(show_result)
        except Exception as exc:
            logger.exception("Failed to sync show %r: %s", title, exc)
            results.append({"title": title, "status": "error", "error": str(exc)})

    created = sum(1 for r in results if r.get("status") == "created")
    updated = sum(1 for r in results if r.get("status") == "updated")

    # ── Mark missing shows as deleted ─────────────────────────────────
    scanned_titles = set(scanned.keys())
    all_shows = await db.execute(
        select(Show).where(Show.deleted == False)  # noqa: E712
    )
    deleted_count = 0
    for show in all_shows.scalars().all():
        if show.title not in scanned_titles:
            show.deleted = True
            deleted_count += 1
    if deleted_count:
        await db.commit()
        logger.info("Soft-deleted %d show(s) no longer on disk", deleted_count)

    return {
        "status": "ok",
        "shows_synced": len(results),
        "created": created,
        "updated": updated,
        "deleted": deleted_count,
        "shows": results,
    }


async def _sync_one_show(
    db: AsyncSession, title: str, scanned_show: ScannedShow, tvdb_available: bool = True
) -> dict[str, Any]:
    """Sync a single scanned show against TVDB and the database."""

    # ── 1. Try to find a TVDB match ─────────────────────────────────────
    tvdb_id: int | None = None
    tvdb_overview: str | None = None
    tvdb_poster: str | None = None
    tvdb_first_aired: str | None = None
    tvdb_seasons: dict[int, int] = {}  # season_number -> tvdb_season_id

    if tvdb_available:
        try:
            search_results = await tvdb.search_show(title)
            if search_results:
                # Pick the first result — could be improved with fuzzy matching
                best_match = search_results[0]
                tvdb_id = _parse_tvdb_id(
                    best_match.get("id") or best_match.get("tvdb_id")
                )
                tvdb_overview = best_match.get("overview") or best_match.get(
                    "description"
                )
                tvdb_poster = (
                    best_match.get("image_url")
                    or best_match.get("image")
                    or best_match.get("poster")
                )

                if tvdb_id:
                    # Get extended show data (overview, poster, season IDs)
                    extended = await tvdb.get_show_extended(tvdb_id)
                    tvdb_overview = (
                        tvdb_overview
                        or extended.get("overview")
                        or extended.get("description")
                    )
                    tvdb_poster = (
                        tvdb_poster
                        or extended.get("image")
                        or extended.get("image_url")
                        or extended.get("poster")
                    )
                    tvdb_first_aired = extended.get("firstAired") or extended.get(
                        "first_aired"
                    )
                    # Build season_number -> tvdb_season_id map from the extended response
                    # Prefer Aired Order / official seasons over alternate orders
                    for s in extended.get("seasons") or []:
                        sn = s.get("number")
                        sid = s.get("id")
                        stype = (s.get("type") or {}).get("type", "")
                        if sn is not None and sid is not None:
                            sn = int(sn)
                            # Only overwrite if this is official, or no entry yet
                            if sn not in tvdb_seasons or stype == "official":
                                tvdb_seasons[sn] = int(sid)
        except Exception:
            logger.warning(
                "TVDB lookup failed for %r, proceeding with local data only", title
            )

    # ── 2. Upsert the Show ──────────────────────────────────────────────
    conditions = [Show.title == title]
    if tvdb_id:
        conditions.append(Show.tvdb_id == tvdb_id)
    result = await db.execute(select(Show).where(or_(*conditions)))
    show = result.scalar_one_or_none()

    is_new = show is None
    if is_new:
        show = Show(
            title=title,
            tvdb_id=tvdb_id,
            overview=tvdb_overview,
            poster_path=tvdb_poster,
            first_aired=tvdb_first_aired,
        )
        db.add(show)
        await db.flush()
    else:
        # Update metadata if we got TVDB data
        if show.deleted:
            show.deleted = False  # show is back on disk
        if tvdb_id and not show.tvdb_id:
            show.tvdb_id = tvdb_id
        if tvdb_overview and not show.overview:
            show.overview = tvdb_overview
        if tvdb_poster and not show.poster_path:
            show.poster_path = tvdb_poster
        if tvdb_first_aired and not show.first_aired:
            show.first_aired = tvdb_first_aired

    # ── 3. Upsert Seasons and Episodes ──────────────────────────────────
    season_summaries = []
    for season_num, scanned_season in sorted(scanned_show.seasons.items()):
        # Find or create the season
        result = await db.execute(
            select(Season).where(
                Season.show_id == show.id, Season.season_number == season_num
            )
        )
        season = result.scalar_one_or_none()

        if season is None:
            season = Season(show_id=show.id, season_number=season_num)
            db.add(season)
            await db.flush()
            # Bump show updated_at when a new season is discovered
            show.updated_at = datetime.now(timezone.utc)

        # Try to get TVDB metadata for this season's episodes
        # Use get_season_extended for full episode details including overview
        tvdb_episodes: dict[int, dict[str, Any]] = {}
        tvdb_season_id = tvdb_seasons.get(season_num)
        if tvdb_season_id:
            try:
                season_ext = await tvdb.get_season_extended(tvdb_season_id)
                for ep in season_ext.get("episodes") or []:
                    ep_num = ep.get("number")
                    if ep_num is not None:
                        tvdb_episodes[int(ep_num)] = ep
            except Exception:
                logger.warning(
                    "Failed to get season extended for season %d", season_num
                )

        # Upsert each scanned episode
        ep_count = 0
        for scanned_ep in scanned_season.episodes:
            ep_num = scanned_ep.episode_number
            result = await db.execute(
                select(Episode).where(
                    Episode.season_id == season.id,
                    Episode.episode_number == ep_num,
                )
            )
            episode = result.scalar_one_or_none()

            tvdb_ep = tvdb_episodes.get(ep_num, {})

            if episode is None:
                episode = Episode(
                    season_id=season.id,
                    episode_number=ep_num,
                    title=tvdb_ep.get("name")
                    or tvdb_ep.get("title")
                    or tvdb_ep.get("episodeName")
                    or scanned_ep.filename,
                    overview=tvdb_ep.get("overview") or tvdb_ep.get("description"),
                    air_date=tvdb_ep.get("aired")
                    or tvdb_ep.get("airDate")
                    or tvdb_ep.get("firstAired")
                    or tvdb_ep.get("air_date"),
                    runtime=tvdb_ep.get("runtime"),
                    file_path=scanned_ep.file_path,
                )
                db.add(episode)
            else:
                # Enrich existing episodes with TVDB metadata
                if not episode.file_path:
                    episode.file_path = scanned_ep.file_path
                if not episode.title:
                    ep_name = (
                        tvdb_ep.get("name")
                        or tvdb_ep.get("title")
                        or tvdb_ep.get("episodeName")
                    )
                    if ep_name:
                        episode.title = ep_name
                if not episode.overview:
                    ep_overview = tvdb_ep.get("overview") or tvdb_ep.get("description")
                    if ep_overview:
                        episode.overview = ep_overview
                if not episode.air_date:
                    ad = (
                        tvdb_ep.get("aired")
                        or tvdb_ep.get("airDate")
                        or tvdb_ep.get("firstAired")
                        or tvdb_ep.get("air_date")
                    )
                    if ad:
                        episode.air_date = ad
                if episode.runtime is None and tvdb_ep.get("runtime"):
                    episode.runtime = tvdb_ep["runtime"]
            ep_count += 1

        season_summaries.append(
            {"season_number": season_num, "episodes_synced": ep_count}
        )

    await db.flush()

    # ── 4. Recalculate part_watched flags ──────────────────────────────
    await _recalc_flags(db, show.id)

    await db.commit()

    return {
        "title": title,
        "show_id": show.id,
        "tvdb_id": tvdb_id,
        "status": "created" if is_new else "updated",
        "seasons": season_summaries,
    }


async def _recalc_flags(db: AsyncSession, show_id: int) -> None:
    """Recalculate watch status for all seasons and the show."""
    result = await db.execute(select(Season).where(Season.show_id == show_id))
    seasons = result.scalars().all()

    for season in seasons:
        ep_result = await db.execute(
            select(Episode).where(Episode.season_id == season.id)
        )
        episodes = ep_result.scalars().all()
        if episodes:
            watched_count = sum(1 for ep in episodes if ep.watched)
            if watched_count == 0:
                season.part_watched = "unwatched"
            elif watched_count == len(episodes):
                season.part_watched = "watched"
            else:
                season.part_watched = "partial"

    show_result = await db.execute(select(Show).where(Show.id == show_id))
    show = show_result.scalar_one()
    statuses = {s.part_watched for s in seasons}
    if statuses == {"unwatched"}:
        show.part_watched = "unwatched"
    elif statuses == {"watched"}:
        show.part_watched = "watched"
    else:
        show.part_watched = "partial"
