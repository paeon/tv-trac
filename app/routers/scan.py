from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.scanner import scan_media_root
from app.services.sync import sync_shows

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scan", tags=["scan"])


@router.post("")
async def trigger_scan(
    persist: bool = Query(default=True, description="Persist results to the database"),
    db: AsyncSession = Depends(get_db),
):
    """
    Scan the configured MEDIA_ROOT for TV shows, seasons, and episodes.

    With `persist=true` (default): matches shows against TheTVDB, creates/updates
    them in the database, and marks episodes as watched when local files exist.

    With `persist=false`: just returns the raw scan results without touching the DB.
    """
    if not persist:
        scanned = scan_media_root()
        result = []
        for title, show in sorted(scanned.items()):
            seasons_data = []
            for season_num, season in sorted(show.seasons.items()):
                seasons_data.append(
                    {
                        "season_number": season_num,
                        "episode_count": len(season.episodes),
                        "episodes": [
                            {
                                "episode_number": ep.episode_number,
                                "file_path": ep.file_path,
                                "filename": ep.filename,
                            }
                            for ep in season.episodes
                        ],
                    }
                )
            result.append(
                {
                    "title": title,
                    "folder_path": show.folder_path,
                    "seasons": seasons_data,
                }
            )
        return {"status": "dry_run", "_count": len(result), "shows": result}

    # Full sync: scan → TVDB → persist
    return await sync_shows(db)
