from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GroupCreate(BaseModel):
    name: str | None = None
    kind: str = "manual"
    smart_field: str | None = None
    smart_value: str | None = None


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    kind: str
    smart_field: str | None
    smart_value: str | None
    show_count: int = 0
    movie_count: int = 0
