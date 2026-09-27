"""Pop-Music scraper plugin for Persian music."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote, urlparse

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
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://pop-music.ir"


class PopMusicPlugin:
    """Pop-Music Iranian music scraper plugin."""

    def __init__(self, config: SourceConfig | None = None):
        self.config = config or SourceConfig(
            id="popmusic",
            name="Pop-Music",
            category=Category.MUSIC,
            base_urls=[DEFAULT_BASE_URL],
            enabled=True,
            timeout_seconds=7.0,
        )

    @property
    def base_url(self) -> str:
        return self.config.primary_base_url or DEFAULT_BASE_URL

    async def search(
        self,
        query: SearchQuery,
        client: AsyncHttpClient,
    ) -> list[MediaItem]:
        """Search Pop-Music for tracks/artists."""
        search_term = query.normalized_query or query.raw_query
        encoded_term = quote(search_term)
        search_url = f"{self.base_url}/?s={encoded_term}"

        try:
            resp = await client.get(search_url, timeout=self.config.timeout_seconds)
            if resp.status_code != 200 or is_parked_page(resp.text):
                logger.warning("Pop-Music search returned %s or parked page", resp.status_code)
                return []
            return self.parse_search_results(resp.text)
        except Exception as e:
            logger.error("Pop-Music search failed: %s", e)
            return []

    def parse_search_results(self, html: str) -> list[MediaItem]:
        """Parse track cards from Pop-Music search page."""
        items: list[MediaItem] = []
        card_pattern = re.compile(
            r'<div class=[\"\']music-card-pro[\"\']>(.*?)</div>\s*</div>\s*</div>',
            re.IGNORECASE | re.DOTALL,
        )

        for match in card_pattern.finditer(html):
            card_html = match.group(1)

            # Extract title and URL
            title_match = re.search(
                r'<a[^>]+href=[\"\']([^\"\']+)[\"\'][^>]*class=[\"\'][^\"\']*music-card-pro__title[^\"\']*[\"\'][^>]*>(.*?)</a>',
                card_html,
                re.DOTALL | re.IGNORECASE,
            )
            if not title_match:
                # Alternative title anchor
                title_match = re.search(
                    r'<a[^>]+aria-label=[\"\']([^\"\']+)[\"\'][^>]+href=[\"\']([^\"\']+)[\"\']',
                    card_html,
                    re.IGNORECASE,
                )
                if not title_match:
                    continue
                raw_title = title_match.group(1).strip()
                raw_url = title_match.group(2).strip()
            else:
                raw_url = title_match.group(1).strip()
                raw_title = title_match.group(2).strip()

            clean_title = re.sub(r"<[^>]+>", "", raw_title).strip()
            post_url = clean_absolute_url(self.base_url, raw_url)
            if not post_url or is_ad_or_shortener_url(post_url):
                continue

            # Extract cover image
            img_match = re.search(r'<img[^>]+src=[\"\']([^\"\']+)[\"\']', card_html, re.IGNORECASE)
            poster_url = clean_absolute_url(self.base_url, img_match.group(1).strip()) if img_match else None

            # Generate item ID from URL path slug
            path_slug = [p for p in urlparse(post_url).path.split("/") if p]
            slug = path_slug[-1] if path_slug else str(len(items) + 1)
            item_id = f"pop_{slug}"

            item = MediaItem(
                id=item_id,
                title=clean_title,
                category=Category.MUSIC,
                source_id=self.config.id,
                page_url=post_url,
                poster_url=poster_url,
            )
            items.append(item)

        return items

    async def extract_links(
        self,
        item: MediaItem,
        client: AsyncHttpClient,
    ) -> MediaItem:
        """Extract 320k, 128k MP3 links and audio stream URL."""
        try:
            resp = await client.get(item.page_url, timeout=self.config.timeout_seconds)
            if resp.status_code != 200 or is_parked_page(resp.text):
                return item
            self.parse_item_page(resp.text, item)
            return item
        except Exception as e:
            logger.error("Pop-Music link extraction failed for %s: %s", item.page_url, e)
            return item

    def parse_item_page(self, html: str, item: MediaItem) -> None:
        """Parse MP3 downloads and audio stream from track page."""
        # Find all MP3 links
        mp3_pattern = re.compile(
            r'href=[\"\']([^\"\']+\.mp3)[\"\']',
            re.IGNORECASE,
        )
        mp3_links = set(mp3_pattern.findall(html))

        downloads: list[MusicDownloadVariant] = []
        stream_url: str | None = None

        # Look for HTML5 audio stream first
        audio_match = re.search(r'<audio[^>]*>.*?<source[^>]+src=[\"\']([^\"\']+)[\"\']', html, re.DOTALL | re.IGNORECASE)
        if audio_match:
            cand_stream = clean_absolute_url(self.base_url, audio_match.group(1).strip())
            if cand_stream and not is_ad_or_shortener_url(cand_stream):
                stream_url = cand_stream

        for link in sorted(mp3_links):
            abs_url = clean_absolute_url(self.base_url, link)
            if not abs_url or is_ad_or_shortener_url(abs_url):
                continue

            if "(128)" in abs_url or "128" in abs_url:
                downloads.append(MusicDownloadVariant(bitrate="128kbps", download_url=abs_url))
                if not stream_url:
                    stream_url = abs_url
            else:
                downloads.append(MusicDownloadVariant(bitrate="320kbps", download_url=abs_url))
                if not stream_url:
                    stream_url = abs_url

        if downloads or stream_url:
            track = MusicTrack(
                id=f"{item.id}_track",
                title=item.title,
                artist="Persian Music",
                source_name=self.config.name,
                cover_url=item.poster_url,
                stream_url=stream_url,
                downloads=downloads,
            )
            item.music_tracks = [track]
            item.stream_url = stream_url
