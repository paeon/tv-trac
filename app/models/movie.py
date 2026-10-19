from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.group import movie_groups

if TYPE_CHECKING:
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    tmdb_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    first_aired: Mapped[str | None] = mapped_column(String(50), nullable=True)
    runtime: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    imdb_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    watchlist: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    watched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    watched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    groups: Mapped[List["Group"]] = relationship(
        "Group", secondary=movie_groups, back_populates="movies", lazy="selectin"
    )

    @property
    def group_names(self) -> list[str]:
        return [g.name for g in self.groups]

    def __repr__(self) -> str:
        return f"<Movie id={self.id} title={self.title!r}>"
