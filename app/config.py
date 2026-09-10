from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # TheTVDB
    tvdb_api_key: str = ""
    tvdb_pin: str = ""

    # TMDB (for movies)
    tmdb_api_key: str = ""

    # Media
    media_root: str = "/media/tv"
    media_root_movies: str = "/media/movies"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/tvtrac.db"

    # Local image cache
    image_dir: str = "./data/images"

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000


settings = Settings()
