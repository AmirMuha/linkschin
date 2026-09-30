"""Fam children's channel plugin (watch_url only, no downloads).

No confirmed reachable address (308 redirect loop per research.md R-001) —
registered, visibly inactive.
"""

from __future__ import annotations

from sources.movies.base_movie import BaseMoviePlugin

class FamPlugin(BaseMoviePlugin):
    """Fam children's channel plugin — not a download portal."""

    DEFAULT_BASE_URL = "https://fam.ir"
    SOURCE_ID = "fam"
    SOURCE_NAME = "Fam"
    PROVIDES_DOWNLOADS = False
    SEARCH_PATH = "/search?q={query}"
