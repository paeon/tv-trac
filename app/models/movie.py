from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

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
    watched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    watched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    def __repr__(self) -> str:
        return f"<Movie id={self.id} title={self.title!r}>"
