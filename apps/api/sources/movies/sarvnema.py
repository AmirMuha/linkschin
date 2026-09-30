"""Sarvnema movie scraper plugin."""

from __future__ import annotations

from sources.movies.base_movie import BaseMoviePlugin


class SarvnemaPlugin(BaseMoviePlugin):
    """Sarvnema movie scraper plugin."""

    DEFAULT_BASE_URL = "https://sarvnema.ir"
    SOURCE_ID = "sarvnema"
    SOURCE_NAME = "Sarvnema"
    PROVIDES_DOWNLOADS = True
    SEARCH_PATH = "/?s={query}"
