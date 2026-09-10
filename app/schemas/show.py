from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

# ── Episode ──────────────────────────────────────────────────────────────────


class EpisodeCreate(BaseModel):
    episode_number: int
    title: str | None = None
    overview: str | None = None
    air_date: str | None = None
    runtime: int | None = None
    watched: bool = False
    file_path: str | None = None


class EpisodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    season_id: int
    episode_number: int
    title: str | None
    overview: str | None
    air_date: str | None
    runtime: int | None
    watched: bool
    watched_at: datetime | None
    file_path: str | None


# ── Season ───────────────────────────────────────────────────────────────────


class SeasonCreate(BaseModel):
    season_number: int
    episodes: list[EpisodeCreate] = []


class SeasonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    show_id: int
    season_number: int
    part_watched: str
    created_at: datetime
    episodes: list[EpisodeOut] = []


# ── Show ─────────────────────────────────────────────────────────────────────


class ShowCreate(BaseModel):
    title: str
    tvdb_id: int | None = None
    overview: str | None = None
    poster_path: str | None = None


class ShowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    tvdb_id: int | None
    tvdb_slug: str | None
    overview: str | None
    poster_path: str | None
    first_aired: str | None
    notes: str | None
    imdb_id: str | None
    missing_count: int
    missing_details: str | None
    hidden: bool
    watchlist: bool
    rating: int
    part_watched: str
    deleted: bool
    created_at: datetime
    updated_at: datetime


class ShowOutNested(ShowOut):
    seasons: list[SeasonOut] = []
