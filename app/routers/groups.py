from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.group import Group
from app.models.movie import Movie
from app.models.show import Show
from app.schemas.group import GroupCreate, GroupOut
from app.services.smart_groups import (
    field_label,
    is_valid_field,
    movie_field_values,
    movie_matches,
    show_field_values,
    show_matches,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("", response_model=List[GroupOut])
async def list_groups(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Group).order_by(Group.name))
    groups = result.scalars().all()

    # Load all shows/movies once to compute smart-group counts.
    shows = (await db.execute(select(Show))).scalars().all()
    movies = (await db.execute(select(Movie))).scalars().all()

    for g in groups:
        if g.is_smart:
            g.show_count = sum(1 for s in shows if show_matches(s, g))
            g.movie_count = sum(1 for m in movies if movie_matches(m, g))
        else:
            g.show_count = len(g.shows)
            g.movie_count = len(g.movies)
    return groups


@router.post("", response_model=GroupOut, status_code=201)
async def create_group(payload: GroupCreate, db: AsyncSession = Depends(get_db)):
    kind = (payload.kind or "manual").strip().lower()
    if kind == "smart":
        field = (payload.smart_field or "").strip().lower()
        value = (payload.smart_value or "").strip()
        if not value:
            raise HTTPException(status_code=400, detail="Smart group value is required")
        if not is_valid_field("show", field) and not is_valid_field("movie", field):
            raise HTTPException(status_code=400, detail="Unknown smart group field")
        name = (payload.name or "").strip() or f"{field_label('show', field)}: {value}"
        group = Group(
            name=name,
            kind="smart",
            smart_field=field,
            smart_value=value,
        )
    else:
        name = (payload.name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Group name is required")
        group = Group(name=name, kind="manual")

    existing = await db.execute(select(Group).where(Group.name == name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Group already exists")

    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


@router.delete("/{group_id}")
async def delete_group(group_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    # Smart groups have no explicit members, so they can be deleted freely.
    if not group.is_smart and (len(group.shows) > 0 or len(group.movies) > 0):
        raise HTTPException(status_code=409, detail="Group is not empty")
    await db.delete(group)
    await db.commit()
    return {"status": "deleted"}


@router.get("/field-values")
async def field_values(
    type: str = Query(...),
    field: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Return distinct values for a smart-group field across the library."""
    if type == "show":
        if not is_valid_field("show", field):
            raise HTTPException(status_code=400, detail="Unknown show field")
        shows = (await db.execute(select(Show))).scalars().all()
        return show_field_values(shows, field)
    if type == "movie":
        if not is_valid_field("movie", field):
            raise HTTPException(status_code=400, detail="Unknown movie field")
        movies = (await db.execute(select(Movie))).scalars().all()
        return movie_field_values(movies, field)
    raise HTTPException(status_code=400, detail="type must be 'show' or 'movie'")
