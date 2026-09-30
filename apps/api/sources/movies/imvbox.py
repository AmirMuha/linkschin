"""IMVBox movie scraper plugin."""

from __future__ import annotations

from sources.movies.base_movie import BaseMoviePlugin


class IMVBoxPlugin(BaseMoviePlugin):
    """IMVBox movie scraper plugin."""

    DEFAULT_BASE_URL = "https://www.imvbox.com"
    SOURCE_ID = "imvbox"
    SOURCE_NAME = "IMVBox"
    PROVIDES_DOWNLOADS = True
    SEARCH_PATH = "/search?q={query}"
