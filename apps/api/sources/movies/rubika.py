"""Rubika children's channel plugin (watch_url only, no downloads)."""

from __future__ import annotations

from sources.movies.base_movie import BaseMoviePlugin

class RubikaPlugin(BaseMoviePlugin):
    """Rubika children's channel plugin — not a download portal."""

    DEFAULT_BASE_URL = "https://rubika.ir"
    SOURCE_ID = "rubika"
    SOURCE_NAME = "Rubika"
    PROVIDES_DOWNLOADS = False
    SEARCH_PATH = "/search?q={query}"
