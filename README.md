# TV-Trac

A self-hosted TV show tracker that scans your local media, enriches it with [TheTVDB](https://thetvdb.com) metadata, and lets you track what you've watched — all in a simple dark-themed web UI.

![TV-Trac](https://img.shields.io/badge/python-3.12-blue) ![Docker](https://img.shields.io/badge/docker-ready-brightgreen)

## Features

- 📁 Scans your local TV folder structure (Show → Season → S01E01 files)
- 🌐 Fetches show/episode metadata from TheTVDB (overviews, air dates, runtimes, posters)
- ✅ Track watched episodes with timestamps, partial/full status at season and show level
- 🔍 Search-as-you-type with filter buttons (All / Watched / Partial / Unwatched)
- 📝 Per-show notes with visual indicator
- 🗑️ Soft-delete — shows removed from disk are hidden but preserved
- 📡 Works offline — just skips TVDB enrichment
- 🐳 Single-container Docker deployment

---

## Prerequisites

- **Docker** and **Docker Compose** installed
- A **TheTVDB API key** — [subscribe](https://www.thetvdb.com/subscribe) ($12/yr) then generate a key at [your dashboard](https://www.thetvdb.com/dashboard/account/apikey)
- Your TV media organised like:

```
/media/tv/
  Breaking Bad/
    Season 01/
      Breaking Bad - S01E01 - Pilot.mkv
      Breaking Bad - S01E02 - Cat's in the Bag.mkv
    Season 02/
      ...
  Better Call Saul/
    Season 01/
      ...
```

Supported filename patterns: `S01E01`, `s01e01`, `1x01`. Video extensions only: `.mkv` `.mp4` `.avi` `.m4v` `.mov` `.wmv` `.flv` `.webm`.

---

## Quick Start — Docker

```bash
# 1. Clone the repo
git clone https://github.com/yourname/tv-trac.git
cd tv-trac

# 2. Create your environment file
cp .env.example .env

# 3. Edit .env with your details
nano .env
```

Your `.env` should look like:

```env
# TheTVDB API key (https://thetvdb.com/dashboard/account/apikey)
TVDB_API_KEY=your_actual_api_key_here
TVDB_PIN=

# Host path to your TV media (mounted read-only inside the container at /media)
MEDIA_HOST_PATH=/path/to/your/tv/shows

# Inside the container — always /media. Docker Compose sets this automatically.
MEDIA_ROOT=/media

# Database (SQLite by default — swap for PostgreSQL for multi-user)
DATABASE_URL=sqlite+aiosqlite:///./data/tvtrac.db
```

```bash
# 4. Start the app
docker compose up -d

# 5. Open your browser
#    Web UI:       http://localhost:8000
#    API docs:     http://localhost:8000/docs

# 6. Click "Scan" in the UI to discover your shows
```

---

## Setup — Dockge

[Dockge](https://github.com/louislam/dockge) is a self-hosted Docker stack manager. Its default paths are:

| Path | Purpose |
|---|---|
| `/opt/dockge` | Dockge installation directory |
| `/opt/stacks` | Where stack compose files live |

### Step 1: Clone the project into the stack directory

```bash
cd /opt/stacks
git clone https://github.com/paeon/tv-trac.git
cd tv-trac
```

This gives you the full project at `/opt/stacks/tv-trac`, including the `Dockerfile`, `.env.example`, and app code.

### Step 2: Create your env file

```bash
cp .env.example .env
nano .env
```

Fill in your TVDB API key and media path (see the Docker section above for the env format).

### Step 3: Build with the bundled compose file (or create your own)

The project already includes a `docker-compose.yml` that works with Dockge with a small adjustment. Dockge looks for `compose.yaml` by default, so either rename it or symlink it:

```bash
ln -s docker-compose.yml compose.yaml
```

The bundled compose file uses `${MEDIA_HOST_PATH}` from your `.env` for the volume mount — this is the cleanest approach for Dockge since all paths are in one place.

If you prefer a static compose file instead, create `/opt/stacks/tv-trac/compose.yaml`:

```yaml
services:
  tvtrac:
    build: .                    # builds from /opt/stacks/tv-trac
    container_name: tvtrac
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data              # persist the database
      - /path/to/your/tv/shows:/media:ro  # your TV media (read-only)
    restart: unless-stopped
```

> **Important:** Replace `/path/to/your/tv/shows` with the actual path to your media directory.

### Step 4: Deploy

In the Dockge web UI, the `tv-trac` stack should appear automatically. Click **Deploy**.

Open `http://your-server:8000` and click **Scan**.

---

## Updating

```bash
# Docker
docker compose down
git pull
docker compose build --no-cache
rm -rf data/          # only if schema changed (check release notes)
docker compose up -d

# Dockge
# Pull latest code, rebuild image, then click "Update & Deploy" in Dockge UI
# Check release notes for whether a database wipe is needed
```

---

## Backup & Restore

The database is a single SQLite file. Back it up by copying:

```bash
# Docker
cp data/tvtrac.db data/tvtrac.db.bak

# Dockge
cp /opt/stacks/tv-trac/data/tvtrac.db /opt/stacks/tv-trac/data/tvtrac.db.bak
```

To restore, stop the container, replace the file, and restart:

```bash
docker compose down
cp data/tvtrac.db.bak data/tvtrac.db
docker compose up -d
```

**Tip:** Run a daily cron job:

```bash
# Add to crontab (crontab -e)
0 3 * * * cp /opt/stacks/tv-trac/data/tvtrac.db /opt/stacks/tv-trac/data/tvtrac.db.$(date +\%Y\%m\%d)
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/shows` | List shows (add `?include_deleted=true` to see removed) |
| `GET` | `/api/shows/{id}` | Get show with nested seasons + episodes |
| `POST` | `/api/shows` | Create a show manually |
| `DELETE` | `/api/shows/{id}` | Delete a show |
| `PATCH` | `/api/shows/{id}/notes?notes=...` | Set or clear show notes |
| `PATCH` | `/api/shows/episodes/{id}/watch?watched=true` | Toggle episode watched |
| `POST` | `/api/scan` | Scan media directory (`?persist=false` for dry-run) |
| `GET` | `/api/tvdb/search?q=breaking+bad` | Search TheTVDB |
| `GET` | `/api/tvdb/shows/{tvdb_id}` | Get TVDB show details |
| `GET` | `/api/tvdb/debug/{tvdb_id}` | Debug TVDB response structure |

---

## Tech Stack

- **Python 3.12** + FastAPI (async backend)
- **SQLAlchemy 2.0** + SQLite (database, swappable to PostgreSQL)
- **httpx** (async TheTVDB v4 API client)
- **Jinja2** + vanilla JS (web UI)
- **Docker** (single-container deployment)

---

## License

MIT
