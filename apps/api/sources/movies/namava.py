"""Namava movie scraper plugin (subscription-only, watch_url)."""

from __future__ import annotations

from sources.movies.base_movie import BaseMoviePlugin

class NamavaPlugin(BaseMoviePlugin):
    """Namava subscription movie scraper plugin."""

    DEFAULT_BASE_URL = "https://namava.ir"
    SOURCE_ID = "namava"
    SOURCE_NAME = "Namava"
    PROVIDES_DOWNLOADS = False
    SEARCH_PATH = "/search/{query}"
