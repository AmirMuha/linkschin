"""BabakFilm movie scraper plugin."""

from __future__ import annotations

from sources.movies.base_movie import BaseMoviePlugin


class BabakFilmPlugin(BaseMoviePlugin):
    """BabakFilm movie scraper plugin."""

    DEFAULT_BASE_URL = "https://babakfilm.com"
    SOURCE_ID = "babakfilm"
    SOURCE_NAME = "BabakFilm"
    PROVIDES_DOWNLOADS = True
    SEARCH_PATH = "/?s={query}"
