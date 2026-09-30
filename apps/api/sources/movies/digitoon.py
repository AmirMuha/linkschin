"""Digitoon children's channel plugin (watch_url only, no downloads)."""

from __future__ import annotations

from sources.movies.base_movie import BaseMoviePlugin

class DigitoonPlugin(BaseMoviePlugin):
    """Digitoon children's channel plugin — not a download portal."""

    DEFAULT_BASE_URL = "https://digitoon.com"
    SOURCE_ID = "digitoon"
    SOURCE_NAME = "Digitoon"
    PROVIDES_DOWNLOADS = False
    SEARCH_PATH = "/search?q={query}"
