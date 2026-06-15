from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.movie import Movie
from app.schemas.movie import MovieCreate, MovieOut
from app.services.movie_sync import sync_movies

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/movies", tags=["movies"])


@router.get("", response_model=List[MovieOut])
async def list_movies(
    include_deleted: bool = False,
    db: AsyncSession = Depends(get_db),
):
    query = select(Movie).order_by(Movie.title)
    if not include_deleted:
        query = query.where(Movie.deleted == False)  # noqa: E712
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{movie_id}", response_model=MovieOut)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.patch("/{movie_id}/watch", response_model=MovieOut)
async def toggle_watched(
    movie_id: int,
    watched: bool = True,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    movie.watched = watched
    movie.watched_at = datetime.now(timezone.utc) if watched else None
    await db.commit()
    await db.refresh(movie)
    return movie


@router.patch("/{movie_id}/notes", response_model=MovieOut)
async def update_notes(
    movie_id: int,
    notes: str = "",
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    movie.notes = notes if notes.strip() else None
    await db.commit()
    await db.refresh(movie)
    return movie


@router.post("/scan")
async def scan_movies(db: AsyncSession = Depends(get_db)):
    """Scan the movies media root, fetch metadata, and persist."""
    return await sync_movies(db)
