# TV-Trac

A self-hosted **TV show and movie tracker** that scans your local media folders, enriches them with metadata from [TheTVDB](https://thetvdb.com) (TV) and [TMDB](https://www.themoviedb.org) (movies), and gives you a clean, filterable web UI to track what you've watched, what you're watching, and what's coming next.

It runs as a single Docker container, stores everything in a local SQLite database, and works fine offline — it just skips metadata enrichment when the API isn't reachable.

---

## Table of contents

- [Features](#features)
- [How it works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Media organisation](#media-organisation)
- [Environment variables](#environment-variables)
- [Quick start — Docker](#quick-start--docker)
- [Setup — Dockge](#setup--dockge)
- [Using the app](#using-the-app)
- [Data & storage](#data--storage)
- [Backup & restore](#backup--restore)
- [Updating](#updating)
- [Logging](#logging)
- [API endpoints](#api-endpoints)
- [Tech stack](#tech-stack)
- [Attribution & license](#attribution--license)

---

## Features

### Media scanning

- Recursively scans your TV and movie directories.
- Supports `Show/Season 01/S01E01.mkv` and `Movie (2023)/Movie (2023).mkv` folder layouts.
- Detects `S01E01`, `s01e01`, and `1x01` filename patterns.
- Video extensions: `.mkv` `.mp4` `.avi` `.m4v` `.mov` `.wmv` `.flv` `.webm`.
- Reads `tvshow.nfo` / `movie.nfo` files when present to get exact titles and TheTVDB/TMDB IDs (useful for ambiguous names).
- Items removed from disk are **soft-deleted** — hidden from listings but kept in the database so history isn't lost.

### Metadata enrichment

- **TheTVDB v4** — show overviews, posters, first-air dates, runtimes, seasons, and full episode details (title, overview, air date, runtime).
- **TMDB v3** — movie overviews, posters, release dates, runtimes, and IMDb IDs.
- **IMDb ID auto-fill** — extracted from TheTVDB's `remoteIds` for shows and TMDB's `imdb_id` for movies; you can also set it manually and the manual value takes precedence.
- **Missing-episode check** — compares your library against TheTVDB and flags shows with missing seasons/episodes (`season 1 missing, 6 episodes` etc.).
- Built-in **rate limiting** to stay within TheTVDB and TMDB API limits (roughly 10 req/s and 4 req/s respectively).
- **Offline-safe** — if the APIs are unreachable, the app still works using only local data.

### Local artwork caching

- Artwork is **preferred from local files first**, then downloaded from TheTVDB/TMDB as a fallback — reducing API load on large libraries.
- Local posters/thumbnails are recognised by Kodi/Plex/Emby conventions: `poster.*`, `folder.*`, `cover.*`, `show.*`, `movie.*`, and episode `{filename}-thumb.*` files next to the video.
- Everything is copied/downloaded to `data/images/{show|movie|season|episode}/` and served locally rather than hot-linked.
- Cached files are reused on subsequent scans.

### Tracking & organisation

- **Watch tracking** — mark episodes and movies watched/unwatched with timestamps.
- **Calendar picker** — set a custom watched date (e.g. if you watched it earlier).
- **Status badges** — Unwatched / Part watched / Watched at the show, season, and movie level.
- **Notes** — editable per show and per movie, with a visual indicator when a note exists.
- **Watchlist** — toggle shows/movies onto a watchlist, with a quick filter and a `WL` badge.
- **Star ratings** — 0–5 stars per show/movie, with per-rating filters and high/low sorting.
- **Hide/unhide** — keep a show/movie in the database but hide it from the main listings (e.g. dropped shows).
- **Ended flag** — mark a show as ended (no more seasons/episodes expected); ended shows are skipped by the missing-episode check.

### UI & browsing

- **Three pages** — Shows, Movies, and Recently Aired Episodes.
- **Grid (default) and list views**, toggleable, with larger poster-centric grid cards.
- **Search-as-you-type** on all pages (with a clear-field button).
- **Filters** — status, watchlist, hidden, ended, rating (1–5 stars), first-aired/release-date (Upcoming, Last month, Last six months, 1/3/5/10 years, and older), and a "New Content" filter (days since added).
- **Sorting** — A–Z, Z–A, Recently Added, First Aired (newest/oldest), Rating (high/low).
- **Pagination** — 10 / 25 / 50 / 100 items per page.
- **Recently Aired Episodes** — a dedicated page listing episodes across all shows, with a toggle between **Recently Aired** (by air date, the default) and **Recently Added** (by when the episode was scanned in), an "Added in" date filter (last 1/3/7/30 days), pagination, search, hide-watched, hidden-show detection, and deep links back to the show/season/episode.
- **Per-show stats** — each show card shows season counts (available · watched · missing) and episode counts (available · watched · missing) at a glance, with missing highlighted, plus the date it was added.
- **Show & movie detail pages** — full metadata, poster, collapsible seasons (expand/collapse all), per-episode watched state, notes, IMDb links, rating, watchlist and hide toggles.
- **Overview popovers** — click the ⓘ icon to read a show/movie/episode overview without cluttering the screen.
- **External links** — to TheTVDB (series), TMDB (movie), and IMDb.
- **Configurable date/time format** — a flag button in the header opens a picker to switch between Default, US, UK, and ISO formats; the choice is remembered in the browser.
- **Configurable content width** — a header toggle switches the layout width between Normal (960px), Wide (1400px), and Full (100%); remembered in the browser.
- **Back to top** — a floating button appears when you scroll down and returns you to the top.
- **Persistent UI state** — filter/search/view selections are remembered in the browser.

---

## How it works

1. **Scan** walks the configured media roots and builds a list of shows/movies, seasons, and episodes from the folder/file structure (using `.nfo` files where available).
2. **Enrich** matches each item against TheTVDB (TV) or TMDB (movies) and fetches metadata + artwork.
3. **Persist** upserts everything into SQLite and downloads artwork into a local image cache.
4. **Serve** exposes a FastAPI backend and a Jinja2/vanilla-JS web UI at `http://localhost:8000`.

The scan is triggered from the **🔍 Scan** button (scans TV then movies), and the **⚠️ Check Missing** button re-checks the TV library against TheTVDB for missing seasons/episodes.

---

## Prerequisites

- **Docker** and **Docker Compose** (or Dockge).
- A **TheTVDB API key** — [subscribe](https://www.thetvdb.com/subscribe) (TheTVDB v4 requires a paid subscription for API access), then generate a key at [your dashboard](https://www.thetvdb.com/dashboard/account/apikey).
- A **TMDB API key** — free at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api).
- Local media organised as described below.

---

## Media organisation

```
TV:
  /media/tv/                          Movies:
    Show Name/                          /media/movies/
      Season 01/                          Movie Name (2023)/
        S01E01 - Episode.mkv                Movie Name (2023).mkv
        S01E02 - Episode.mkv              Another Movie/
      Season 02/                            Another Movie.mp4
        S01E01 - Episode.mkv
```

- TV shows are expected in a `Show Name/Season NN/` structure.
- Movies are expected in a `Movie Name (Year)/` folder (or directly as files).

---

## Environment variables

All settings are read from the `.env` file. Values marked **"set by compose"** are overridden inside `docker-compose.yml` and do not need to be changed.

| Variable | Required | Default | Description |
|---|---|---|---|
| `TVDB_API_KEY` | Yes | — | TheTVDB v4 API key |
| `TVDB_PIN` | No | — | Optional TheTVDB subscriber PIN |
| `TMDB_API_KEY` | Yes | — | TMDB API key (movie metadata) |
| `MEDIA_HOST_TV_PATH` | Yes (Docker) | `/media/tv` | **Host** path to your TV library (mounted into the container) |
| `MEDIA_HOST_MOVIES_PATH` | Yes (Docker) | `/media/movies` | **Host** path to your movie library (mounted into the container) |
| `MEDIA_ROOT` | No | `/media/tv` | **Container** path to TV media (set by compose) |
| `MEDIA_ROOT_MOVIES` | No | `/media/movies` | **Container** path to movie media (set by compose) |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./data/tvtrac.db` | SQLAlchemy database URL |
| `IMAGE_DIR` | No | `./data/images` | Local artwork cache directory |
| `APP_HOST` | No | `0.0.0.0` | Bind address |
| `APP_PORT` | No | `8000` | Bind port |
| `LOG_LEVEL` | No | `INFO` | Log verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

> **Note:** `MEDIA_HOST_TV_PATH` and `MEDIA_HOST_MOVIES_PATH` are used only by Docker Compose for the volume mounts. Inside the container the media is always at `/media/tv` and `/media/movies` (see `MEDIA_ROOT` / `MEDIA_ROOT_MOVIES`).

---

## Quick start — Docker

```bash
git clone https://github.com/paeon/tv-trac.git
cd tv-trac
cp .env.example .env
nano .env     # add your API keys and host media paths
docker compose up -d --build
```

Open `http://localhost:8000`, then click **🔍 Scan**.

### `.env` example

```env
# TheTVDB API credentials
TVDB_API_KEY=your_tvdb_api_key_here
TVDB_PIN=

# TMDB API key for movie metadata
TMDB_API_KEY=your_tmdb_api_key_here

# Host paths to your media (mounted inside the container at /media/tv and /media/movies)
MEDIA_HOST_TV_PATH=/home/tony/server
MEDIA_HOST_MOVIES_PATH=/home/tony/server/movies

# Inside the container — docker-compose sets these automatically
MEDIA_ROOT=/media/tv
MEDIA_ROOT_MOVIES=/media/movies

# Database (SQLite by default)
DATABASE_URL=sqlite+aiosqlite:///./data/tvtrac.db

# Optional local artwork cache location
IMAGE_DIR=./data/images

# Application settings
APP_HOST=0.0.0.0
APP_PORT=8000

# Logging verbosity (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

---

## Setup — Dockge

Dockge typically stores its own data under `/opt/dockge` and stacks under `/opt/stacks`.

1. Clone the repo into the stacks directory:

```bash
cd /opt/stacks
git clone https://github.com/paeon/tv-trac.git
cd tv-trac
```

2. Create and edit the environment file:

```bash
cp .env.example .env
nano .env
```

3. Create the `compose.yaml` symlink that Dockge expects:

```bash
ln -s docker-compose.yml compose.yaml
```

4. In the Dockge UI, open the `tv-trac` stack and click **Start/Deploy**.

---

## Using the app

| Page | What you can do |
|---|---|
| **Shows** | Search, filter, sort, switch grid/list, mark watched status, add notes, rate, watchlist, hide/unhide, mark ended, open the detail page |
| **Movies** | Same as shows, but for movies |
| **Recently Aired Episodes** | Toggle between Recently Aired (default) and Recently Added, filter by "added in" date range, search, sort, hide watched, paginate, and jump to a show/season/episode |
| **Show detail** | Poster, overview, IMDb/TVDB links, notes, rating, watchlist/hide/ended toggles, first-aired + added dates, collapsible seasons, per-episode watched + calendar dates |
| **Movie detail** | Poster, overview, IMDb/TMDB links, notes, rating, watchlist/hide toggles, released + added dates, watched + calendar date |

**Common actions:**

- **Scan** — the `🔍 Scan` button in the header scans TV shows then movies, with a live "Scanning shows… / Scanning movies…" status, an elapsed timer, and a **Cancel scan** button. The page header switches to "Scanning shows and movies…" during the scan and is restored on refresh.
- **Check Missing** — the `⚠️ Check Missing` button re-checks TV shows against TheTVDB and flags missing seasons/episodes.
- **Mark watched** — click an episode/movie watched badge; use the calendar link to set a custom date.
- **Change date/time format** — click the flag button in the header to switch between Default, US, UK, and ISO formats.
- **Change content width** — click the `← 960px →` button in the header to cycle between Normal, Wide, and Full widths.
- **Hide a show/movie** — from its detail page ("Hide from listings"). Hidden items still appear when searching under **All**, labelled `hidden`, and can be unhidden from there or the detail page.

---

## Data & storage

- **Database** — a single SQLite file at `data/tvtrac.db` (persisted via the `./data:/app/data` volume).
- **Artwork** — downloaded to `data/images/{show|movie|season|episode}/` and served by the app under `/images/...`.

The data model:

| Table | Key fields |
|---|---|
| `shows` | `title`, `tvdb_id`, `tvdb_slug`, `overview`, `poster_path`, `first_aired`, `notes`, `imdb_id`, `missing_count`, `missing_details`, `missing_season_count`, `ended`, `hidden`, `watchlist`, `rating`, `part_watched`, `deleted`, `created_at`, `updated_at` |
| `seasons` | `show_id`, `season_number`, `poster_path`, `part_watched`, `created_at` |
| `episodes` | `season_id`, `episode_number`, `title`, `overview`, `air_date`, `runtime`, `watched`, `watched_at`, `file_path`, `image_path`, `created_at` |
| `movies` | `title`, `tmdb_id`, `overview`, `poster_path`, `first_aired`, `runtime`, `notes`, `imdb_id`, `hidden`, `watchlist`, `rating`, `watched`, `watched_at`, `file_path`, `deleted`, `created_at`, `updated_at` |

> **Schema changes:** the app uses `create_all` plus a small startup migration that applies *additive* column changes automatically (e.g. `episodes.created_at`) without touching your data. Destructive changes still require a wipe and rescan: `docker compose down && rm -rf data/ && docker compose up -d --build`, then scan again.

---

## Backup & restore

The entire state is the SQLite database (and optionally the cached images). To back up:

```bash
# Simple file copy
cp data/tvtrac.db data/tvtrac.db.bak

# Daily cron example (Dockge path)
0 3 * * * cp /opt/stacks/tv-trac/data/tvtrac.db /opt/stacks/tv-trac/data/tvtrac.db.$(date +\%Y\%m\%d)
```

To restore, stop the container, replace `data/tvtrac.db`, and start again:

```bash
docker compose down
cp data/tvtrac.db.bak data/tvtrac.db
docker compose up -d
```

---

## Updating

```bash
cd tv-trac
git pull
docker compose up -d --build
```

If a release changes the schema (noted in the changelog/commit), wipe and rescan:

```bash
docker compose down
rm -rf data/
docker compose up -d --build
# then scan from the UI
```

---

## Logging

Logs go to the container's stdout/stderr — view them with `docker compose logs -f tvtrac`.

The default level (`INFO`) shows scan progress and any warnings/errors, including connection failures, timeouts, and HTTP 4xx/5xx responses (e.g. API rate-limiting/`429`). For full detail — every API request and rate-limit throttling — set `LOG_LEVEL=DEBUG` in `.env` and restart.

```bash
docker compose logs -f tvtrac
```

---

## API endpoints

### Shows

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/shows` | List shows (`?include_hidden=true`, `?include_deleted=true`) |
| `GET` | `/api/shows/{id}` | Show with nested seasons + episodes |
| `POST` | `/api/shows` | Create a show |
| `DELETE` | `/api/shows/{id}` | Delete a show |
| `PATCH` | `/api/shows/{id}/notes?notes=...` | Set/clear notes |
| `PATCH` | `/api/shows/{id}/imdb?imdb_id=...` | Set/clear IMDb ID |
| `PATCH` | `/api/shows/{id}/hidden?hidden=true` | Hide/unhide |
| `PATCH` | `/api/shows/{id}/ended?ended=true` | Mark as ended/ongoing |
| `PATCH` | `/api/shows/{id}/watchlist?watchlist=true` | Add/remove from watchlist |
| `PATCH` | `/api/shows/{id}/rating?rating=3` | Set 0–5 rating |
| `PATCH` | `/api/shows/episodes/{id}/watch?watched=true&watched_at=YYYY-MM-DD` | Toggle episode watched (optional custom date) |

### Movies

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/movies` | List movies (`?include_deleted=true`) |
| `GET` | `/api/movies/{id}` | Movie details |
| `PATCH` | `/api/movies/{id}/watch?watched=true&watched_at=YYYY-MM-DD` | Toggle movie watched |
| `PATCH` | `/api/movies/{id}/notes?notes=...` | Set/clear notes |
| `PATCH` | `/api/movies/{id}/imdb?imdb_id=...` | Set/clear IMDb ID |
| `PATCH` | `/api/movies/{id}/hidden?hidden=true` | Hide/unhide |
| `PATCH` | `/api/movies/{id}/watchlist?watchlist=true` | Add/remove from watchlist |
| `PATCH` | `/api/movies/{id}/rating?rating=3` | Set 0–5 rating |
| `POST` | `/api/movies/scan` | Scan movies only |

### Scan & episodes

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/scan` | Scan TV (`?persist=false` for dry-run) |
| `GET` | `/api/scan/check-missing?store=true` | Check TV for missing seasons/episodes |
| `GET` | `/api/episodes/recent?limit=50&order=desc&exclude_watched=false` | Recently aired episodes |

### TheTVDB debug

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/tvdb/search?q=...` | Search TheTVDB |
| `GET` | `/api/tvdb/shows/{tvdb_id}` | Raw TheTVDB show |
| `GET` | `/api/tvdb/debug/{tvdb_id}` | Debug TVDB response |
| `GET` | `/api/tvdb/debug-movie/{tvdb_id}` | Debug raw movie response |

### Web pages

| Path | Description |
|---|---|
| `/` | Shows / movies / recent-episodes tabs |
| `/show/{id}` | Show detail page |
| `/movie/{id}` | Movie detail page |
| `/recent-episodes` | Recently aired episodes |

---

## Tech stack

- **Python 3.12** + **FastAPI**
- **SQLAlchemy 2.0** + **aiosqlite** (SQLite)
- **httpx** — async TheTVDB v4 and TMDB v3 clients (rate-limited)
- **Jinja2** + vanilla JavaScript (no front-end build step)
- **Docker** (single `python:3.12-slim` container)

---

## Attribution & license

- TV metadata and artwork provided by [TheTVDB](https://thetvdb.com) — the footer links back for attribution.
- Movie metadata and artwork provided by [TMDB](https://www.themoviedb.org) — also linked in the footer.

Licensed under the **MIT License**.
