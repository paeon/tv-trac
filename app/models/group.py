"""
User-defined groups for organising shows and movies.

Groups are simple named buckets that shows and movies can be added to via
many-to-many association tables. The UI lets you create groups, assign items
to them, and filter the listings by group.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.movie import Movie
    from app.models.show import Show


def _now() -> datetime:
    return datetime.now(timezone.utc)


# Many-to-many association tables (string FK refs avoid circular imports).
show_groups = Table(
    "show_groups",
    Base.metadata,
    Column("show_id", Integer, ForeignKey("shows.id"), primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id"), primary_key=True),
)

movie_groups = Table(
    "movie_groups",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id"), primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id"), primary_key=True),
)


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    shows: Mapped[List["Show"]] = relationship(
        "Show", secondary=show_groups, back_populates="groups", lazy="selectin"
    )
    movies: Mapped[List["Movie"]] = relationship(
        "Movie", secondary=movie_groups, back_populates="groups", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Group id={self.id} name={self.name!r}>"
