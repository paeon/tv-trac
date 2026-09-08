from __future__ import annotations

import logging
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import init_db
from app.models.movie import Movie  # noqa: F401 — register model
from app.routers import movies, scan, shows, tvdb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables if they don't exist
    await init_db()
    yield
    # Shutdown: nothing to clean up for SQLite


app = FastAPI(
    title="TV-Trac",
    description="Track your TV shows — mark episodes watched, scan local files, and enrich with TheTVDB metadata.",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount static files (CSS, JS, images)
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Global exception handler — logs full traceback and returns it for debugging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    logger.error("Unhandled exception: %s\n%s", exc, tb)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "traceback": tb.split("\n")},
    )


# API routers
app.include_router(shows.router)
app.include_router(scan.router)
app.include_router(tvdb.router)
app.include_router(movies.router)


# ── Web UI ───────────────────────────────────────────────────────────────────


@app.get("/")
async def index(request: Request):
    """Serve the main web UI."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "media_tv": settings.media_root,
            "media_movies": settings.media_root_movies,
        },
    )


@app.get("/show/{show_id}")
async def show_detail(request: Request, show_id: int):
    """Serve a dedicated show detail page."""
    return templates.TemplateResponse(
        "show_detail.html",
        {"request": request, "show_id": show_id},
    )
