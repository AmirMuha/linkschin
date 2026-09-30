"""Nda Media movie scraper plugin."""

from __future__ import annotations

from sources.movies.base_movie import BaseMoviePlugin


class NdaMediaPlugin(BaseMoviePlugin):
    """Nda Media scraper plugin."""

    DEFAULT_BASE_URL = "https://ndamedia.ir"
    SOURCE_ID = "ndamedia"
    SOURCE_NAME = "Nda Media"
    PROVIDES_DOWNLOADS = True
    SEARCH_PATH = "/?s={query}"
