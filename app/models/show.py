from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Show(Base):
    __tablename__ = "shows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    tvdb_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    first_aired: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    part_watched: Mapped[str] = mapped_column(
        String(10), default="unwatched", nullable=False
    )
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    seasons: Mapped[List["Season"]] = relationship(
        "Season", back_populates="show", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Show id={self.id} title={self.title!r}>"


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id"), nullable=False)
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    part_watched: Mapped[str] = mapped_column(
        String(10), default="unwatched", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    show: Mapped[Show] = relationship("Show", back_populates="seasons")
    episodes: Mapped[List["Episode"]] = relationship(
        "Episode",
        back_populates="season",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Season show_id={self.show_id} season={self.season_number}>"


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), nullable=False)
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    air_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    runtime: Mapped[int | None] = mapped_column(Integer, nullable=True)
    watched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    watched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    season: Mapped[Season] = relationship("Season", back_populates="episodes")

    def __repr__(self) -> str:
        return f"<Episode season_id={self.season_id} ep={self.episode_number}>"
