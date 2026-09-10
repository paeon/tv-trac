from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.show import Episode, Season, Show

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/episodes", tags=["episodes"])


@router.get("/recent")
async def recent_episodes(
    limit: int = Query(default=50, ge=1, le=500),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    exclude_watched: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the most recently aired episodes (up to `limit`), across all shows.

    The most recent `limit` episodes are selected by air date, then sorted
    by the requested `order` for display. Hidden shows are included so that
    newly-started seasons are surfaced; the caller can flag them via
    `show_hidden` and offer to unhide the show.
    """
    query = (
        select(Episode, Season, Show)
        .join(Season, Episode.season_id == Season.id)
        .join(Show, Season.show_id == Show.id)
        .where(Show.deleted == False)  # noqa: E712
        .where(Episode.air_date.isnot(None))
        .order_by(Episode.air_date.desc())
    )
    if exclude_watched:
        query = query.where(Episode.watched == False)  # noqa: E712
    query = query.limit(limit)
    result = await db.execute(query)
    rows = result.all()

    episodes: List[dict] = []
    for ep, season, show in rows:
        episodes.append(
            {
                "id": ep.id,
                "title": ep.title,
                "episode_number": ep.episode_number,
                "season_number": season.season_number,
                "air_date": ep.air_date,
                "runtime": ep.runtime,
                "watched": ep.watched,
                "watched_at": ep.watched_at.isoformat() if ep.watched_at else None,
                "overview": ep.overview,
                "show_id": show.id,
                "show_title": show.title,
                "show_slug": show.tvdb_slug,
                "show_poster": show.poster_path,
                "show_hidden": show.hidden,
                "episode_image": ep.image_path,
            }
        )

    if order == "asc":
        episodes.reverse()

    return {"episodes": episodes, "count": len(episodes)}
