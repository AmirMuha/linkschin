"""Filmnet movie scraper plugin (subscription-only, watch_url)."""

from __future__ import annotations

from sources.movies.base_movie import BaseMoviePlugin

class FilmnetPlugin(BaseMoviePlugin):
    """Filmnet subscription movie scraper plugin."""

    DEFAULT_BASE_URL = "https://filmnet.ir"
    SOURCE_ID = "filmnet"
    SOURCE_NAME = "Filmnet"
    PROVIDES_DOWNLOADS = False
    SEARCH_PATH = "/search?q={query}"
    # Real content lives under /contents/<id>/<slug>; /contents?types= is the
    # genre filter, not a result.
    ITEM_URL_SUBSTRING = "/contents/"
