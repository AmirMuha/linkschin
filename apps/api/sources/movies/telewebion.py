"""Telewebion movie scraper plugin."""

from __future__ import annotations

from sources.movies.base_movie import BaseMoviePlugin


class TelewebionPlugin(BaseMoviePlugin):
    """Telewebion movie scraper plugin."""

    DEFAULT_BASE_URL = "https://telewebion.ir"
    SOURCE_ID = "telewebion"
    SOURCE_NAME = "Telewebion"
    PROVIDES_DOWNLOADS = True
    SEARCH_PATH = "/search?q={query}"
