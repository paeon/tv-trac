from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.group import Group
from app.schemas.group import GroupCreate, GroupOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("", response_model=List[GroupOut])
async def list_groups(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Group).order_by(Group.name))
    groups = result.scalars().all()
    for g in groups:
        g.show_count = len(g.shows)
        g.movie_count = len(g.movies)
    return groups


@router.post("", response_model=GroupOut, status_code=201)
async def create_group(payload: GroupCreate, db: AsyncSession = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Group name is required")
    existing = await db.execute(select(Group).where(Group.name == name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Group already exists")
    group = Group(name=name)
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
    await db.delete(group)
    await db.commit()
    return {"status": "deleted"}
