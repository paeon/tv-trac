from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MovieCreate(BaseModel):
    title: str
    tmdb_id: int | None = None
    overview: str | None = None
    poster_path: str | None = None
    first_aired: str | None = None
    runtime: int | None = None


class MovieOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    tmdb_id: int | None
    overview: str | None
    poster_path: str | None
    first_aired: str | None
    runtime: int | None
    notes: str | None
    imdb_id: str | None
    hidden: bool
    watchlist: bool
    rating: int
    watched: bool
    watched_at: datetime | None
    file_path: str | None
    deleted: bool
    created_at: datetime
    updated_at: datetime
