# TV-Trac

A self-hosted TV show and movie tracker that scans your local media, enriches it with [TheTVDB](https://thetvdb.com) and [TMDB](https://www.themoviedb.org) metadata, and lets you track what you've watched.

## Features

- 📁 **Media scanning** — parses `Show/Season 01/S01E01.mkv` and `Movie (2023)/` folder structures
- 📋 **NFO support** — reads `tvshow.nfo` / `movie.nfo` for exact titles and IDs
- 🌐 **TheTVDB integration** — series metadata: overviews, posters, air dates, runtimes, season/episode details
- 🎬 **TMDB integration** — movie metadata: overviews, posters, release dates, runtimes
- ✅ **Watch tracking** — toggle episodes/movies watched with timestamps
- 🏷️ **Status badges** — Unwatched / Part watched / Watched at show, season, and movie level
- 🔍 **Search + filters** — search-as-you-type, filter by status, sort A-Z or Recently Added
- 📄 **Pagination** — 10/25/50/100 items per page
- 📝 **Per-show/movie notes** — editable inline with visual indicator
- ⓘ **Info popovers** — click for overviews without cluttering the UI
- 🖼️ **Poster thumbnails** — sourced from TheTVDB/TMDB
- 🔗 **External links** — ↗ to TheTVDB/TMDB pages
- 🗑️ **Soft-delete** — shows/movies removed from disk are hidden but preserved
- 📡 **Offline-safe** — works without internet, just skips metadata enrichment
- 🗓️ **UK date formatting** — abbreviated month names (Jun 14, 2026)
- 🐳 **Single-container Docker** deployment

## Prerequisites

- **Docker** and **Docker Compose**
- **TheTVDB API key** — [subscribe](https://www.thetvdb.com/subscribe) ($12/yr) then generate a key at [your dashboard](https://www.thetvdb.com/dashboard/account/apikey)
- **TMDB API key** — free at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)
- Media organised as:

```
TV:
  /media/tv/                      Movies:
    Show Name/                      /media/movies/
      Season 01/                      Movie Name (2023)/
        S01E01 - Episode.mkv            Movie Name (2023).mkv
        S01E02 - Episode.mkv          Another Movie/
      Season 02/                        Another Movie.mp4
        ...
```

Supported filename patterns: `S01E01`, `s01e01`, `1x01`. Video extensions: `.mkv` `.mp4` `.avi` `.m4v` `.mov` `.wmv` `.flv` `.webm`.

## Quick Start — Docker

```bash
git clone https://github.com/paeon/tv-trac.git
cd tv-trac
cp .env.example .env
nano .env    # add your API keys and media paths
docker compose up -d
```

Open `http://localhost:8000` and click **Scan**.

### .env example

```env
TVDB_API_KEY=your_tvdb_key
TVDB_PIN=
TMDB_API_KEY=your_tmdb_key
MEDIA_HOST_TV_PATH=/home/user/tv
MEDIA_HOST_MOVIES_PATH=/home/user/movies
MEDIA_ROOT=/media/tv
MEDIA_ROOT_MOVIES=/media/movies
DATABASE_URL=sqlite+aiosqlite:///./data/tvtrac.db
```

## Setup — Dockge

```bash
cd /opt/stacks
git clone https://github.com/paeon/tv-trac.git
cd tv-trac
cp .env.example .env
nano .env
ln -s docker-compose.yml compose.yaml
```

Then deploy from the Dockge UI.

## Backup

The database is a single SQLite file:

```bash
# Backup
cp data/tvtrac.db data/tvtrac.db.bak

# Daily cron
0 3 * * * cp /opt/stacks/tv-trac/data/tvtrac.db /opt/stacks/tv-trac/data/tvtrac.db.$(date +\%Y\%m\%d)
```

## Updating

```bash
docker compose down
git pull
docker compose build --no-cache
rm -rf data/            # only if schema changed
docker compose up -d
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/shows` | List shows (`?include_deleted=true`) |
| `GET` | `/api/shows/{id}` | Show with nested seasons + episodes |
| `PATCH` | `/api/shows/{id}/notes?notes=...` | Set/clear show notes |
| `PATCH` | `/api/shows/episodes/{id}/watch?watched=true` | Toggle episode watched |
| `GET` | `/api/movies` | List movies |
| `PATCH` | `/api/movies/{id}/watch?watched=true` | Toggle movie watched |
| `PATCH` | `/api/movies/{id}/notes?notes=...` | Set/clear movie notes |
| `POST` | `/api/scan` | Scan TV + movies (`?persist=false` for dry-run) |
| `POST` | `/api/movies/scan` | Scan movies only |
| `GET` | `/api/settings` | Get app settings |
| `GET` | `/api/tvdb/search?q=...` | Search TheTVDB |
| `GET` | `/api/tvdb/debug/{id}` | Debug TVDB response |

## Tech Stack

- **Python 3.12** + FastAPI
- **SQLAlchemy 2.0** + SQLite
- **httpx** — async TheTVDB v4 + TMDB v3 clients
- **Jinja2** + vanilla JS
- **Docker**

## License

MIT
