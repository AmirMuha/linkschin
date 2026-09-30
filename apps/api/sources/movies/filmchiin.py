"""FilmChiin movie scraper plugin."""

from __future__ import annotations

from sources.movies.base_movie import BaseMoviePlugin


class FilmChiinPlugin(BaseMoviePlugin):
    """FilmChiin movie scraper plugin."""

    DEFAULT_BASE_URL = "https://filmchiin.ir"
    SOURCE_ID = "filmchiin"
    SOURCE_NAME = "FilmChiin"
    PROVIDES_DOWNLOADS = True
    SEARCH_PATH = "/?s={query}"
