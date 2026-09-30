"""Danfilo movie scraper plugin."""

from __future__ import annotations

from sources.movies.base_movie import BaseMoviePlugin


class DanfiloPlugin(BaseMoviePlugin):
    """Danfilo movie scraper plugin."""

    DEFAULT_BASE_URL = "https://danfilo.ir"
    SOURCE_ID = "danfilo"
    SOURCE_NAME = "Danfilo"
    PROVIDES_DOWNLOADS = True
    SEARCH_PATH = "/?s={query}"
