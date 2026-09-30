"""Aparat movie scraper plugin — uses the public search API (T031).

Aparat renders search client-side and serves zero search markup to a plain GET,
so the HTML parser inherited from base_movie finds nothing. The same public
endpoint the page calls returns JSON, so this plugin reads that instead.
"""

from __future__ import annotations

import json
import logging
from urllib.parse import quote

from http_client import AsyncHttpClient
from models import Category, MediaItem, SearchQuery, SourceConfig
from sources.base import clean_absolute_url

logger = logging.getLogger(__name__)


class AparatPlugin:
    """Aparat video scraper backed by the public search API."""

    DEFAULT_BASE_URL = "https://www.aparat.com"
    SOURCE_ID = "aparat"
    SOURCE_NAME = "Aparat"
    PROVIDES_DOWNLOADS = True
    SEARCH_PATH = "/api/fa/v1/video/video/search/text/{query}?filter=all&page=1"

    def __init__(self, config: SourceConfig | None = None):
        self.config = config or SourceConfig(
            id=self.SOURCE_ID,
            name=self.SOURCE_NAME,
            category=Category.MOVIES,
            base_urls=[self.DEFAULT_BASE_URL],
            enabled=True,
            provides_downloads=self.PROVIDES_DOWNLOADS,
            timeout_seconds=7.0,
        )

    @property
    def base_url(self) -> str:
        return self.config.primary_base_url or self.DEFAULT_BASE_URL

    def build_search_url(self, search_term: str) -> str:
        return clean_absolute_url(self.base_url, self.SEARCH_PATH.format(query=quote(search_term)))

    async def search(self, query: SearchQuery, client: AsyncHttpClient) -> list[MediaItem]:
        term = query.normalized_query or query.raw_query
        try:
            resp = await client.get(
                self.build_search_url(term), timeout=self.config.timeout_seconds
            )
            if resp.status_code != 200:
                return []
            return self.parse_search_results(resp.text)
        except Exception as e:
            logger.error("%s search failed: %s", self.config.name, e)
            return []

    def parse_search_results(self, html: str) -> list[MediaItem]:
        """Parse an API JSON payload. Non-JSON input yields no items, never raises."""
        try:
            data = json.loads(html)
        except (ValueError, TypeError):
            return []
        if not isinstance(data, dict):
            return []

        items: list[MediaItem] = []
        seen: set[str] = set()
        for entry in data.get("included") or []:
            if not isinstance(entry, dict) or entry.get("type") != "Video":
                continue
            attrs = entry.get("attributes") or {}
            title = attrs.get("title")
            if isinstance(title, dict):  # the API nests the label under "text"
                title = title.get("text")
            title = (title or "").strip()
            if not title:
                continue

            # uid is the public video hash used in /v/<hash> URLs.
            vid = str(attrs.get("uid") or attrs.get("id") or "").strip()
            if not vid:
                continue
            abs_url = clean_absolute_url(self.base_url, f"/v/{vid}")
            if abs_url in seen:
                continue
            seen.add(abs_url)

            poster = attrs.get("big_poster") or attrs.get("medium_poster") or attrs.get("small_poster")
            items.append(
                MediaItem(
                    id=f"{self.config.id}_{vid}",
                    title=title,
                    category=Category.MOVIES,
                    source_id=self.config.id,
                    page_url=abs_url,
                    poster_url=clean_absolute_url(self.base_url, poster) if poster else None,
                    # FR-006: a video host is not a download portal, so no
                    # download variant is ever constructed from this item.
                    watch_url=abs_url,
                    movie_variants=[],
                )
            )
        return items

    def parse_item_page(self, html: str, target: MediaItem) -> None:
        """Aparat streams via its own player; nothing to extract (FR-026)."""
        target.movie_variants = []
        target.stream_url = None
        target.watch_url = target.watch_url or target.page_url

    async def extract_links(self, item: MediaItem, client: AsyncHttpClient) -> MediaItem:
        item.movie_variants = []
        item.stream_url = None
        item.watch_url = item.watch_url or item.page_url
        return item
