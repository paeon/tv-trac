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

    # Smart-group metadata columns (additive)
    show_cols = {
        "genres": "TEXT",
        "network": "VARCHAR(200)",
        "country": "VARCHAR(100)",
        "language": "VARCHAR(100)",
        "status": "VARCHAR(50)",
    }
    for col, ctype in show_cols.items():
        if col not in columns:
            await conn.execute(
                text(f"ALTER TABLE shows ADD COLUMN {col} {ctype}")
            )

    result = await conn.execute(text("PRAGMA table_info(movies)"))
    columns = [row[1] for row in result.fetchall()]
    movie_cols = {
        "genres": "TEXT",
        "studio": "VARCHAR(200)",
        "country": "VARCHAR(100)",
        "language": "VARCHAR(100)",
    }
    for col, ctype in movie_cols.items():
        if col not in columns:
            await conn.execute(
                text(f"ALTER TABLE movies ADD COLUMN {col} {ctype}")
            )

    result = await conn.execute(text("PRAGMA table_info(groups)"))
    columns = [row[1] for row in result.fetchall()]
    group_cols = {
        "kind": "VARCHAR(20) NOT NULL DEFAULT 'manual'",
        "smart_field": "VARCHAR(50)",
        "smart_value": "VARCHAR(200)",
    }
    for col, ctype in group_cols.items():
        if col not in columns:
            await conn.execute(
                text(f"ALTER TABLE groups ADD COLUMN {col} {ctype}")
            )
