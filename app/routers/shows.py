from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.show import Episode, Season, Show
from app.schemas.show import (
    EpisodeCreate,
    EpisodeOut,
    SeasonOut,
    ShowCreate,
    ShowOut,
    ShowOutNested,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/shows", tags=["shows"])

# ── Shows ────────────────────────────────────────────────────────────────────


@router.get("", response_model=List[ShowOut])
async def list_shows(
    include_deleted: bool = False,
    db: AsyncSession = Depends(get_db),
):
    query = select(Show).order_by(Show.title)
    if not include_deleted:
        query = query.where(Show.deleted == False)  # noqa: E712
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{show_id}", response_model=ShowOutNested)
async def get_show(show_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Show)
        .options(selectinload(Show.seasons).selectinload(Season.episodes))
        .where(Show.id == show_id)
    )
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    return show


@router.post("", response_model=ShowOut, status_code=201)
async def create_show(payload: ShowCreate, db: AsyncSession = Depends(get_db)):
    show = Show(**payload.model_dump())
    db.add(show)
    await db.commit()
    await db.refresh(show)
    return show


@router.delete("/{show_id}", status_code=204)
async def delete_show(show_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Show).where(Show.id == show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    await db.delete(show)
    await db.commit()


@router.patch("/{show_id}/notes", response_model=ShowOut)
async def update_notes(
    show_id: int,
    notes: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Set or clear notes on a show."""
    result = await db.execute(select(Show).where(Show.id == show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    show.notes = notes if notes.strip() else None
    await db.commit()
    await db.refresh(show)
    return show


# ── Episodes ─────────────────────────────────────────────────────────────────


@router.patch("/episodes/{episode_id}/watch", response_model=EpisodeOut)
async def toggle_watched(
    episode_id: int,
    watched: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Mark an episode as watched (or unwatched), updating part_watched flags."""
    result = await db.execute(select(Episode).where(Episode.id == episode_id))
    episode = result.scalar_one_or_none()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    episode.watched = watched
    episode.watched_at = datetime.now(timezone.utc) if watched else None
    await db.flush()

    # Recalculate part_watched for the parent season
    await _recalc_season_part_watched(episode.season_id, db)
    # Recalculate part_watched for the parent show (needs season's show_id)
    season_result = await db.execute(
        select(Season).where(Season.id == episode.season_id)
    )
    season = season_result.scalar_one()
    await _recalc_show_part_watched(season.show_id, db)

    await db.commit()
    await db.refresh(episode)
    return episode


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _recalc_season_part_watched(season_id: int, db: AsyncSession) -> None:
    """Update a season's watch status based on its episodes."""
    result = await db.execute(select(Episode).where(Episode.season_id == season_id))
    episodes = result.scalars().all()
    if not episodes:
        return
    watched_count = sum(1 for ep in episodes if ep.watched)
    season = (
        await db.execute(select(Season).where(Season.id == season_id))
    ).scalar_one()
    if watched_count == 0:
        season.part_watched = "unwatched"
    elif watched_count == len(episodes):
        season.part_watched = "watched"
    else:
        season.part_watched = "partial"


async def _recalc_show_part_watched(show_id: int, db: AsyncSession) -> None:
    """Update a show's watch status based on its seasons."""
    result = await db.execute(select(Season).where(Season.show_id == show_id))
    seasons = result.scalars().all()
    if not seasons:
        return
    show = (await db.execute(select(Show).where(Show.id == show_id))).scalar_one()
    statuses = {s.part_watched for s in seasons}
    if statuses == {"unwatched"}:
        show.part_watched = "unwatched"
    elif statuses == {"watched"}:
        show.part_watched = "watched"
    else:
        show.part_watched = "partial"
