"""YouTube Music reference plugin: link-out to the licensed service's search page."""

from __future__ import annotations

from urllib.parse import quote_plus
from models import SearchQuery, SourceConfig
from sources.music.reference import ReferenceSourcePlugin


class YoutubeMusicPlugin(ReferenceSourcePlugin):
    """YouTube Music reference plugin: link-out to the licensed service's search page."""

    def search_url(self, query: SearchQuery) -> str:
        """Override default search URL."""
        term = query.normalized_query or query.raw_query
        return f"{self.base_url}/search?q={quote_plus(term)}"

