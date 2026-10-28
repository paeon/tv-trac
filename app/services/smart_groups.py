"""
Smart groups: rule-based (dynamic) membership from stored metadata.

A smart group stores a ``smart_field`` + ``smart_value`` pair and its membership
is computed on the fly by matching a show/movie's stored metadata fields.
"""

from __future__ import annotations

import json
from typing import Any

# field key -> human label (used in auto-generated names and the UI)
SHOW_FIELDS = {
    "genre": "Genre",
    "network": "Network",
    "country": "Country",
    "language": "Language",
    "status": "Status",
    "year": "Year",
}

MOVIE_FIELDS = {
    "genre": "Genre",
    "studio": "Studio",
    "country": "Country",
    "language": "Language",
    "year": "Year",
}


def field_label(kind: str, field: str) -> str:
    """Return a human label for a field, defaulting to the field key."""
    mapping = MOVIE_FIELDS if kind == "movie" else SHOW_FIELDS
    return mapping.get(field, field.title())


def is_valid_field(kind: str, field: str) -> bool:
    mapping = MOVIE_FIELDS if kind == "movie" else SHOW_FIELDS
    return field in mapping


def _load_genres(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(data, list):
        return [str(x) for x in data if x]
    return []


def _year(first_aired: str | None) -> str:
    return (first_aired or "")[:4]


def show_matches(show: Any, group: Any) -> bool:
    """Return True if a show matches a smart group's rule."""
    field = group.smart_field
    value = (group.smart_value or "").strip().lower()
    if not field or not value:
        return False

    if field == "genre":
        return value in {g.lower() for g in _load_genres(show.genres)}
    if field == "network":
        return (show.network or "").strip().lower() == value
    if field == "country":
        return (show.country or "").strip().lower() == value
    if field == "language":
        return (show.language or "").strip().lower() == value
    if field == "status":
        return (show.status or "").strip().lower() == value
    if field == "year":
        return _year(show.first_aired) == value
    return False


def movie_matches(movie: Any, group: Any) -> bool:
    """Return True if a movie matches a smart group's rule."""
    field = group.smart_field
    value = (group.smart_value or "").strip().lower()
    if not field or not value:
        return False

    if field == "genre":
        return value in {g.lower() for g in _load_genres(movie.genres)}
    if field == "studio":
        return (movie.studio or "").strip().lower() == value
    if field == "country":
        return (movie.country or "").strip().lower() == value
    if field == "language":
        return (movie.language or "").strip().lower() == value
    if field == "year":
        return _year(movie.first_aired) == value
    return False


def show_field_values(shows: list[Any], field: str) -> list[str]:
    """Distinct, sorted values for a show field across the library."""
    values: set[str] = set()
    for s in shows:
        if field == "genre":
            values.update(_load_genres(s.genres))
        elif field == "network":
            if s.network:
                values.add(s.network)
        elif field == "country":
            if s.country:
                values.add(s.country)
        elif field == "language":
            if s.language:
                values.add(s.language)
        elif field == "status":
            if s.status:
                values.add(s.status)
        elif field == "year":
            y = _year(s.first_aired)
            if y:
                values.add(y)
    return sorted(values)


def movie_field_values(movies: list[Any], field: str) -> list[str]:
    """Distinct, sorted values for a movie field across the library."""
    values: set[str] = set()
    for m in movies:
        if field == "genre":
            values.update(_load_genres(m.genres))
        elif field == "studio":
            if m.studio:
                values.add(m.studio)
        elif field == "country":
            if m.country:
                values.add(m.country)
        elif field == "language":
            if m.language:
                values.add(m.language)
        elif field == "year":
            y = _year(m.first_aired)
            if y:
                values.add(y)
    return sorted(values)
