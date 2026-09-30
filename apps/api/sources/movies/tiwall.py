"""Tiwall movie scraper plugin (subscription-only, watch_url).

No confirmed reachable address (307 redirect loop per research.md R-001); the
bounded-redirect handling in http_client surfaces the loop instead of hanging.
"""

from __future__ import annotations

from sources.movies.base_movie import BaseMoviePlugin

class TiwallPlugin(BaseMoviePlugin):
    """Tiwall subscription movie scraper plugin."""

    DEFAULT_BASE_URL = "https://tiwall.com"
    SOURCE_ID = "tiwall"
    SOURCE_NAME = "Tiwall"
    PROVIDES_DOWNLOADS = False
    SEARCH_PATH = "/search?q={query}"
