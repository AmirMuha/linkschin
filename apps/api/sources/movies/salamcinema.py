"""Salam Cinema scraper plugin (subscription-only, watch_url).

No confirmed reachable address (research.md R-001) — registered, visibly inactive.
"""

from __future__ import annotations

from sources.movies.base_movie import BaseMoviePlugin

class SalamCinemaPlugin(BaseMoviePlugin):
    """Salam Cinema subscription movie scraper plugin."""

    DEFAULT_BASE_URL = "https://salamscinema.io"
    SOURCE_ID = "salamcinema"
    SOURCE_NAME = "Salam Cinema"
    PROVIDES_DOWNLOADS = False
    SEARCH_PATH = "/search?q={query}"
