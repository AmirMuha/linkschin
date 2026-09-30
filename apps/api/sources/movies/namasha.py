"""Namasha movie scraper plugin (subscription-only, watch_url)."""

from __future__ import annotations

from sources.movies.base_movie import BaseMoviePlugin

class NamashaPlugin(BaseMoviePlugin):
    """Namasha subscription movie scraper plugin."""

    DEFAULT_BASE_URL = "https://namasha.com"
    SOURCE_ID = "namasha"
    SOURCE_NAME = "Namasha"
    PROVIDES_DOWNLOADS = False
    SEARCH_PATH = "/search?q={query}"
    # A watch page is /v/<hash>. /playlist/ and /channel* are account chrome.
    ITEM_URL_SUBSTRING = "/v/"
