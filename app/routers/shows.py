from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.group import Group
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
    include_hidden: bool = False,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Show)
        .options(selectinload(Show.seasons).selectinload(Season.episodes))
        .order_by(Show.title)
    )
    if not include_deleted:
        query = query.where(Show.deleted == False)  # noqa: E712
    if not include_hidden:
        query = query.where(Show.hidden == False)  # noqa: E712
    result = await db.execute(query)
    shows = result.scalars().all()
    for show in shows:
        seasons = show.seasons
        episodes = [ep for season in seasons for ep in season.episodes]
        show.season_count = len(seasons)
        show.watched_season_count = sum(
            1 for s in seasons if s.part_watched == "watched"
        )
        show.episode_count = len(episodes)
        show.watched_episode_count = sum(1 for ep in episodes if ep.watched)
    return shows


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


@router.patch("/{show_id}/imdb", response_model=ShowOut)
async def update_imdb(
    show_id: int,
    imdb_id: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Set or clear the IMDb ID on a show."""
    result = await db.execute(select(Show).where(Show.id == show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    show.imdb_id = imdb_id.strip() if imdb_id.strip() else None
    await db.commit()
    await db.refresh(show)
    return show


@router.patch("/{show_id}/hidden", response_model=ShowOut)
async def toggle_hidden(
    show_id: int,
    hidden: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Hide or unhide a show from listings."""
    result = await db.execute(select(Show).where(Show.id == show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    show.hidden = hidden
    await db.commit()
    await db.refresh(show)
    return show


@router.patch("/{show_id}/watchlist", response_model=ShowOut)
async def toggle_watchlist(
    show_id: int,
    watchlist: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Add or remove a show from the watchlist."""
    result = await db.execute(select(Show).where(Show.id == show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    show.watchlist = watchlist
    await db.commit()
    await db.refresh(show)
    return show


@router.patch("/{show_id}/ended", response_model=ShowOut)
async def toggle_ended(
    show_id: int,
    ended: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Mark a show as ended (no more seasons/episodes expected)."""
    result = await db.execute(select(Show).where(Show.id == show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    show.ended = ended
    await db.commit()
    await db.refresh(show)
    return show


@router.patch("/{show_id}/rating", response_model=ShowOut)
async def set_rating(
    show_id: int,
    rating: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Set a 0-5 star rating on a show (0 = unrated)."""
    result = await db.execute(select(Show).where(Show.id == show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    show.rating = max(0, min(5, rating))
    await db.commit()
    await db.refresh(show)
    return show


# ── Groups ───────────────────────────────────────────────────────────────────


@router.post("/{show_id}/groups/{group_id}", response_model=ShowOut)
async def add_show_to_group(
    show_id: int, group_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Show).options(selectinload(Show.groups)).where(Show.id == show_id)
    )
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    group = (
        await db.execute(select(Group).where(Group.id == group_id))
    ).scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if not any(g.id == group_id for g in show.groups):
        show.groups.append(group)
        await db.commit()
    return show


@router.delete("/{show_id}/groups/{group_id}", response_model=ShowOut)
async def remove_show_from_group(
    show_id: int, group_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Show).options(selectinload(Show.groups)).where(Show.id == show_id)
    )
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    for g in list(show.groups):
        if g.id == group_id:
            show.groups.remove(g)
            await db.commit()
            break
    return show


# ── Episodes ─────────────────────────────────────────────────────────────────


@router.patch("/episodes/{episode_id}/watch", response_model=EpisodeOut)
async def toggle_watched(
    episode_id: int,
    watched: bool = True,
    watched_at: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Mark an episode as watched (or unwatched), updating part_watched flags.

    Optionally accepts a `watched_at` date string (YYYY-MM-DD) to set a
    custom watched timestamp instead of using the current time.
    """
    result = await db.execute(select(Episode).where(Episode.id == episode_id))
    episode = result.scalar_one_or_none()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    episode.watched = watched
    if watched:
        if watched_at:
            try:
                episode.watched_at = datetime.fromisoformat(watched_at)
            except ValueError:
                episode.watched_at = datetime.now(timezone.utc)
        elif episode.watched_at is None:
            episode.watched_at = datetime.now(timezone.utc)
    else:
        episode.watched_at = None
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
