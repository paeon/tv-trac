from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GroupCreate(BaseModel):
    name: str


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    show_count: int = 0
    movie_count: int = 0
