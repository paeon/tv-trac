"""
Compare local library against TheTVDB to detect missing seasons and episodes.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.show import Episode, Season, Show
from app.services.tvdb import tvdb

logger = logging.getLogger(__name__)


async def check_missing(db: AsyncSession, store: bool = False) -> dict[str, Any]:
    """For each show, compare local episodes against TheTVDB and report gaps.

    If `store` is True, also persist the results to the Show records.
    """

    result = await db.execute(select(Show).where(Show.deleted == False))  # noqa: E712
    shows = result.scalars().all()

    tvdb_available = False
    try:
        await tvdb.authenticate()
        tvdb_available = True
    except Exception:
        logger.warning("TVDB unavailable — cannot check for missing episodes")

    if not tvdb_available:
        return {"status": "offline", "message": "TheTVDB is unreachable", "shows": []}

    report = []
    for show in shows:
        if not show.tvdb_id:
            if store:
                show.missing_count = 0
                show.missing_details = None
                show.missing_season_count = 0
            report.append(
                {
                    "title": show.title,
                    "status": "no_tvdb",
                    "message": "No TVDB ID — skipping",
                }
            )
            continue

        try:
            r = await _check_one_show(db, show)
            report.append(r)
            if store:
                show.missing_count = r.get("missing_count", 0)
                show.missing_details = (
                    r.get("message") if r.get("missing_count", 0) > 0 else None
                )
                show.missing_season_count = r.get("missing_season_count", 0)
        except Exception as exc:
            logger.exception("Failed to check %r: %s", show.title, exc)
            report.append(
                {
                    "title": show.title,
                    "status": "error",
                    "message": str(exc),
                }
            )

    if store:
        await db.commit()

    return {"status": "ok", "shows": report}


async def _check_one_show(db: AsyncSession, show: Show) -> dict[str, Any]:
    """Check a single show against TVDB."""
    extended = await tvdb.get_show_extended(show.tvdb_id)

    # Build tvdb season map (prefer official)
    tvdb_seasons: dict[int, int] = {}
    for s in extended.get("seasons") or []:
        sn = s.get("number")
        sid = s.get("id")
        stype = (s.get("type") or {}).get("type", "")
        if sn is not None and sid is not None:
            sn = int(sn)
            if sn not in tvdb_seasons or stype == "official":
                tvdb_seasons[sn] = int(sid)

    # Get local seasons and episode counts
    local_seasons_result = await db.execute(
        select(Season).where(Season.show_id == show.id)
    )
    local_seasons = local_seasons_result.scalars().all()
    local_counts: dict[int, int] = {}
    for season in local_seasons:
        ep_result = await db.execute(
            select(Episode).where(Episode.season_id == season.id)
        )
        local_counts[season.season_number] = len(ep_result.scalars().all())

    missing_details = []
    total_missing = 0
    missing_season_count = 0

    # For each TVDB season (skip season 0 = specials)
    for season_num in sorted(tvdb_seasons.keys()):
        if season_num == 0:
            continue

        tvdb_season_id = tvdb_seasons[season_num]
        season_ext = await tvdb.get_season_extended(tvdb_season_id)
        tvdb_episodes = season_ext.get("episodes") or []
        tvdb_count = len(tvdb_episodes)

        local_count = local_counts.get(season_num, 0)

        if tvdb_count == 0:
            continue  # no episodes listed, skip

        missing_count = max(0, tvdb_count - local_count)
        if missing_count > 0:
            total_missing += missing_count
            if local_count == 0:
                missing_season_count += 1
            missing_details.append(
                {
                    "season": season_num,
                    "missing_count": missing_count,
                    "tvdb_count": tvdb_count,
                    "local_count": local_count,
                }
            )

    if not missing_details:
        return {
            "title": show.title,
            "status": "ok",
            "message": "All seasons correct",
            "missing_count": 0,
            "missing_season_count": 0,
        }

    return {
        "title": show.title,
        "status": "missing",
        "message": _format_message(missing_details, total_missing),
        "missing": missing_details,
        "missing_count": total_missing,
        "missing_season_count": missing_season_count,
    }


def _format_message(missing: list[dict], total: int) -> str:
    parts = []
    for m in missing:
        if m["local_count"] == 0:
            parts.append(
                f"Season {m['season']} missing ({m['missing_count']} episodes)"
            )
        else:
            parts.append(f"Season {m['season']} missing {m['missing_count']} episodes")
    return "; ".join(parts)
