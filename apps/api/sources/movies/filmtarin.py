"""FilmTarin movie scraper plugin."""

from __future__ import annotations

from sources.movies.base_movie import BaseMoviePlugin


class FilmTarinPlugin(BaseMoviePlugin):
    """FilmTarin movie scraper plugin."""

    DEFAULT_BASE_URL = "https://filmtarin.com"
    SOURCE_ID = "filmtarin"
    SOURCE_NAME = "FilmTarin"
    PROVIDES_DOWNLOADS = True
    SEARCH_PATH = "/?s={query}"
