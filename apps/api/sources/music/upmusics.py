"""UpMusics scraper plugin (upmusics.com) for Persian music."""

from __future__ import annotations

import logging
import re
from urllib.parse import unquote, urlparse

from http_client import AsyncHttpClient
from models import (
    Category,
    MediaItem,
    MusicDownloadVariant,
    MusicTrack,
    SearchQuery,
    SourceConfig,
)
from sources.base import (
    clean_absolute_url,
    is_ad_or_shortener_url,
    is_parked_page,
    mp3_bitrate,
    split_track_names,
    wp_card_link,
    wp_card_poster,
    wp_cards,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://upmusics.com"
CARD_CLASS = "upsng"


class UpMusicsPlugin:
    """UpMusics Iranian music portal scraper."""

    def __init__(self, config: SourceConfig | None = None):
        self.config = config or SourceConfig(
            id="upmusics",
            name="UpMusics",
            category=Category.MUSIC,
            base_urls=[DEFAULT_BASE_URL],
        )

    @property
    def base_url(self) -> str:
        return self.config.primary_base_url or DEFAULT_BASE_URL

    async def search(
        self,
        query: SearchQuery,
        client: AsyncHttpClient,
    ) -> list[MediaItem]:
        """Search UpMusics for tracks."""
        term = query.normalized_query or query.raw_query
        search_url = f"{self.base_url}/?s={term}"
        try:
            resp = await client.get(search_url, timeout=self.config.timeout_seconds)
            if resp.status_code != 200 or is_parked_page(resp.text):
                logger.warning("UpMusics search returned %s or parked page", resp.status_code)
                return []
            return self.parse_search_results(resp.text)
        except Exception as e:
            logger.error("UpMusics search failed: %s", e)
            return []

    def parse_search_results(self, html: str) -> list[MediaItem]:
        """Parse track cards from UpMusics search results. Never raises."""
        try:
            items: list[MediaItem] = []
            for block in wp_cards(html, CARD_CLASS):
                url, title = wp_card_link(block, self.base_url)
                if not url:
                    continue
                slug = unquote(urlparse(url).path.rstrip("/").rsplit("/", 1)[-1])
                items.append(
                    MediaItem(
                        id=f"upm_{slug}",
                        title=title,
                        category=Category.MUSIC,
                        source_id=self.config.id,
                        page_url=url,
                        poster_url=wp_card_poster(block, self.base_url),
                    )
                )
            return items
        except Exception as e:
            logger.error("UpMusics search parse failed: %s", e)
            return []

    async def extract_links(
        self,
        item: MediaItem,
        client: AsyncHttpClient,
    ) -> MediaItem:
        """Fetch the track page and pull its MP3 links."""
        try:
            resp = await client.get(item.page_url, timeout=self.config.timeout_seconds)
            if resp.status_code != 200 or is_parked_page(resp.text):
                return item
            self.parse_item_page(resp.text, item)
            return item
        except Exception as e:
            logger.error("UpMusics link extraction failed for %s: %s", item.page_url, e)
            return item

    def parse_item_page(self, html: str, item: MediaItem) -> None:
        """Populate stream_url and downloads list. No links -> no change (FR-015)."""
        downloads: list[MusicDownloadVariant] = []
        seen: set[str] = set()
        for m in re.finditer(
            r'<a[^>]+href=["\']([^"\']+\.mp3)[^"\']*["\'][^>]*>(.{0,250}?)</a>',
            html,
            re.DOTALL | re.IGNORECASE,
        ):
            url = clean_absolute_url(self.base_url, m.group(1).strip())
            if not url or url in seen or is_ad_or_shortener_url(url):
                continue
            seen.add(url)
            downloads.append(
                MusicDownloadVariant(
                    bitrate=mp3_bitrate(url, re.sub(r"<[^>]+>", " ", m.group(2))),
                    download_url=url,
                )
            )
        if not downloads:
            return

        by_bitrate = {d.bitrate: d.download_url for d in downloads}
        stream_url = by_bitrate.get("128kbps") or downloads[0].download_url
        artist, title = split_track_names(item.title)
        item.music_tracks = [
            MusicTrack(
                id=f"{item.id}_track",
                title=title,
                artist=artist or "Unknown Artist",
                source_name=self.config.name,
                cover_url=item.poster_url,
                stream_url=stream_url,
                downloads=downloads,
            )
        ]
        item.stream_url = stream_url
