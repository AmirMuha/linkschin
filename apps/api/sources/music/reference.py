"""Base class for reference (link-out only) source plugins.

Constitution Principle III (No Media Relaying) is upheld structurally: this class
has NO code path that sets ``stream_url`` or ``music_tracks`` on a MediaItem.
``extract_links`` is a no-op that returns the item unchanged, so even when the
search pipeline calls it, a reference item can never gain media (FR-011).

No credentials, tokens, or account identifiers are accepted anywhere (FR-012):
the constructor takes only a SourceConfig.
"""

from __future__ import annotations

import logging
import zlib
from urllib.parse import quote_plus

from http_client import AsyncHttpClient
from models import Category, MediaItem, SearchQuery, SourceConfig

logger = logging.getLogger(__name__)


class ReferenceSourcePlugin:
    """Link-out reference source: one result per query pointing at the site's own search page.

    ponytail: a reference result links to the source's search URL for the query
    instead of scraping JS-rendered per-track pages (Spotify/YouTube/etc). Per
    brief 006 this pass is explicitly scoped to link-out breadth; upgrade to
    per-site scraping only when a specific host proves cheap to parse.
    """

    def __init__(self, config: SourceConfig):
        self.config = config

    @property
    def base_url(self) -> str:
        return self.config.primary_base_url

    def search_url(self, query: SearchQuery) -> str:
        """Where a listener lands when they click the card; subclasses may override."""
        term = query.normalized_query or query.raw_query
        return f"{self.base_url}/?s={quote_plus(term)}"

    async def search(
        self,
        query: SearchQuery,
        client: AsyncHttpClient,
    ) -> list[MediaItem]:
        """Return the link-out card without any upstream HTTP call."""
        term = query.normalized_query or query.raw_query
        if not term:
            return []
        url = self.search_url(query)
        return [
            MediaItem(
                # crc32, not hash(): str hashing is salted per process, so the same
                # query would get a different id after every restart.
                id=f"ref_{self.config.id}_{zlib.crc32(term.encode()):08x}",
                title=f"{self.config.name}: {term}",
                category=Category.MUSIC,
                source_id=self.config.id,
                page_url=url,
                # Reference items NEVER get stream_url or music_tracks (FR-011);
                # there is deliberately no assignment path here.
            )
        ]

    async def extract_links(
        self,
        item: MediaItem,
        client: AsyncHttpClient,
    ) -> MediaItem:
        """No-op by design — a reference source has nothing to extract (FR-011)."""
        return item
