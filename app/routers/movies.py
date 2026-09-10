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
    watched_at: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    movie.watched = watched
    if watched:
        if watched_at:
            try:
                movie.watched_at = datetime.fromisoformat(watched_at)
            except ValueError:
                movie.watched_at = datetime.now(timezone.utc)
        elif movie.watched_at is None:
            movie.watched_at = datetime.now(timezone.utc)
    else:
        movie.watched_at = None
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


@router.patch("/{movie_id}/imdb", response_model=MovieOut)
async def update_imdb(
    movie_id: int,
    imdb_id: str = "",
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    movie.imdb_id = imdb_id.strip() if imdb_id.strip() else None
    await db.commit()
    await db.refresh(movie)
    return movie


@router.patch("/{movie_id}/hidden", response_model=MovieOut)
async def toggle_hidden(
    movie_id: int,
    hidden: bool = True,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    movie.hidden = hidden
    await db.commit()
    await db.refresh(movie)
    return movie


@router.patch("/{movie_id}/watchlist", response_model=MovieOut)
async def toggle_watchlist(
    movie_id: int,
    watchlist: bool = True,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    movie.watchlist = watchlist
    await db.commit()
    await db.refresh(movie)
    return movie


@router.patch("/{movie_id}/rating", response_model=MovieOut)
async def set_rating(
    movie_id: int,
    rating: int = 0,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    movie.rating = max(0, min(5, rating))
    await db.commit()
    await db.refresh(movie)
    return movie


@router.post("/scan")
async def scan_movies(db: AsyncSession = Depends(get_db)):
    """Scan the movies media root, fetch metadata, and persist."""
    return await sync_movies(db)
