from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.tvdb import tvdb

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tvdb", tags=["tvdb"])


@router.get("/search")
async def search_show(q: str):
    """Search TheTVDB for a show by name."""
    try:
        results = await tvdb.search_show(q)
        return {"results": results}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TheTVDB error: {exc}")


@router.get("/shows/{tvdb_id}")
async def get_show(tvdb_id: int):
    """Fetch full show details from TheTVDB by ID."""
    try:
        data = await tvdb.get_show_extended(tvdb_id)
        return {"show": data}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TheTVDB error: {exc}")


@router.get("/debug/{tvdb_id}")
async def debug_show(tvdb_id: int):
    """Compare season-extended vs episode-extended to see where overviews live."""
    try:
        extended = await tvdb.get_show_extended(tvdb_id)

        # Find first real season (number > 0)
        season_id = None
        for s in extended.get("seasons") or []:
            if (s.get("number") or 0) > 0:
                season_id = s.get("id")
                break

        season_ep = None
        extended_ep = None

        # What the sync calls: get_season_extended
        if season_id:
            se = await tvdb.get_season_extended(season_id)
            se_eps = se.get("episodes") or []
            season_ep = se_eps[0] if se_eps else None
            # Also try per-episode extended for the first episode
            if season_ep:
                try:
                    extended_ep = await tvdb.get_episode_extended(season_ep["id"])
                except Exception:
                    pass

        return {
            "show_overview": extended.get("overview"),
            "season_extended_first": season_ep,
            "episode_extended_first": extended_ep,
            "season_extended_has_overview": bool(
                season_ep and season_ep.get("overview")
            ),
            "episode_extended_has_overview": bool(
                extended_ep and extended_ep.get("overview")
            ),
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TheTVDB error: {exc}")


@router.get("/debug-movie/{tvdb_id}")
async def debug_movie(tvdb_id: int):
    """Return the RAW movie extended response to see field names."""
    try:
        data = await tvdb.get_movie_extended(tvdb_id)
        return {
            "keys": list(data.keys()) if data else [],
            "name": data.get("name"),
            "overview": data.get("overview"),
            "firstAired": data.get("firstAired"),
            "releaseDate": data.get("releaseDate"),
            "first_release": data.get("first_release"),
            "runtime": data.get("runtime"),
            "image": data.get("image"),
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TheTVDB error: {exc}")
