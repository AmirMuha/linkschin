"""Gapfilm movie scraper plugin."""

from __future__ import annotations

from sources.movies.base_movie import BaseMoviePlugin


class GapfilmPlugin(BaseMoviePlugin):
    """Gapfilm movie scraper plugin."""

    DEFAULT_BASE_URL = "https://gapfilm.ir"
    SOURCE_ID = "gapfilm"
    SOURCE_NAME = "Gapfilm"
    PROVIDES_DOWNLOADS = True
    SEARCH_PATH = "/?s={query}"
