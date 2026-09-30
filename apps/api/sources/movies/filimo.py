"""Filimo movie scraper plugin (subscription-only, watch_url)."""

from __future__ import annotations

from sources.movies.base_movie import BaseMoviePlugin


class FilimoPlugin(BaseMoviePlugin):
    """Filimo subscription movie scraper plugin."""

    DEFAULT_BASE_URL = "https://www.filimo.com"
    SOURCE_ID = "filimo"
    SOURCE_NAME = "Filimo"
    PROVIDES_DOWNLOADS = False
    SEARCH_PATH = "/search/{query}"
