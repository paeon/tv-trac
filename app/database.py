from __future__ import annotations

from app.config import settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:  # type: ignore[reportUnknownParameterType]
    async with async_session() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate(conn)


async def _migrate(conn) -> None:
    """Apply additive schema changes for existing databases.

    ``create_all`` only creates missing tables; it never alters existing ones,
    so new columns are added here (idempotently).
    """
    result = await conn.execute(text("PRAGMA table_info(episodes)"))
    columns = [row[1] for row in result.fetchall()]
    if "created_at" not in columns:
        await conn.execute(
            text("ALTER TABLE episodes ADD COLUMN created_at DATETIME")
        )
        # Backfill existing episodes from their season's created_at — the
        # best available approximation of when they were first scanned in.
        await conn.execute(
            text(
                "UPDATE episodes SET created_at = COALESCE("
                "(SELECT seasons.created_at FROM seasons "
                " WHERE seasons.id = episodes.season_id), "
                "'1970-01-01 00:00:00')"
            )
        )

    result = await conn.execute(text("PRAGMA table_info(shows)"))
    columns = [row[1] for row in result.fetchall()]
    if "last_aired" not in columns:
        await conn.execute(
            text("ALTER TABLE shows ADD COLUMN last_aired VARCHAR(50)")
        )
