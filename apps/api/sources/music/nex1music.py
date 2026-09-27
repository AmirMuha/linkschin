"""Nex1Music scraper plugin for Persian music."""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import quote, unquote

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

DEFAULT_BASE_URL = "https://nex1music.com"

# Theme assets (like/download icons) live here; the poster is the only real cover image.
_ICON_MARKER = "/themev4/"


class Nex1MusicPlugin:
    """Nex1Music Iranian music scraper plugin."""

    def __init__(self, config: SourceConfig | None = None):
        self.config = config or SourceConfig(
            id="nex1music",
            name="Nex1Music",
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
        """Search Nex1Music for tracks."""
        search_term = query.normalized_query or query.raw_query
        search_url = f"{self.base_url}/search/{quote(search_term)}/"

        try:
            resp = await client.get(search_url, timeout=self.config.timeout_seconds)
            if resp.status_code != 200 or is_parked_page(resp.text):
                logger.warning("Nex1Music search returned %s or parked page", resp.status_code)
                return []
            return self.parse_search_results(resp.text)
        except Exception as e:
            logger.error("Nex1Music search failed: %s", e)
            return []

    def parse_search_results(self, html: str) -> list[MediaItem]:
        """Parse post cards from Nex1Music search results."""
        items: list[MediaItem] = []

        for block in html.split('<div class="post anm">')[1:]:
            # Post ID lives in the like counter's rel attribute; fall back to URL slug.
            id_match = re.search(r'<div class="plike" rel="(\d+)"', block)
            link_match = re.search(
                r'<h2><a href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                block,
                re.DOTALL | re.IGNORECASE,
            )
            if not link_match:
                continue

            post_url = clean_absolute_url(self.base_url, link_match.group(1).strip())
            if not post_url or is_ad_or_shortener_url(post_url):
                continue

            title = re.sub(r"<[^>]+>", "", link_match.group(2)).strip()
            if id_match:
                item_id = f"nex_{id_match.group(1)}"
            else:
                slug = [p for p in unquote(post_url).rstrip("/").split("/") if p][-1]
                item_id = f"nex_{slug}"

            # Cover is the first non-icon <img> inside the card body.
            poster_url = None
            for src in re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', block, re.IGNORECASE):
                if _ICON_MARKER in src:
                    continue
                candidate = clean_absolute_url(self.base_url, src.strip())
                if candidate and not is_ad_or_shortener_url(candidate):
                    poster_url = candidate
                    break

            items.append(
                MediaItem(
                    id=item_id,
                    title=title,
                    category=Category.MUSIC,
                    source_id=self.config.id,
                    page_url=post_url,
                    poster_url=poster_url,
                )
            )

        return items

    async def extract_links(
        self,
        item: MediaItem,
        client: AsyncHttpClient,
    ) -> MediaItem:
        """Extract 320k/128k/64k MP3 links and audio stream URL."""
        try:
            resp = await client.get(item.page_url, timeout=self.config.timeout_seconds)
            if resp.status_code != 200 or is_parked_page(resp.text):
                return item
            self.parse_item_page(resp.text, item)
            return item
        except Exception as e:
            logger.error("Nex1Music link extraction failed for %s: %s", item.page_url, e)
            return item

    def parse_item_page(self, html: str, item: MediaItem) -> None:
        """Parse MP3 download variants and audio stream from a track page."""
        downloads: list[MusicDownloadVariant] = []
        seen: set[str] = set()

        # Each download is an <a href="...mp3"> wrapping a div.dllink with a quality label.
        for match in re.finditer(
            r'<a href=["\']([^"\']+\.mp3)["\'][^>]*>(.*?)</a>',
            html,
            re.DOTALL | re.IGNORECASE,
        ):
            url = clean_absolute_url(self.base_url, match.group(1).strip())
            if not url or url in seen or is_ad_or_shortener_url(url):
                continue

            label = re.sub(r"<[^>]+>", " ", match.group(2))
            if "128" in url or "128" in label:
                bitrate = "128kbps"
            elif "64" in url or "64" in label:
                bitrate = "64kbps"
            else:
                bitrate = "320kbps"

            seen.add(url)
            downloads.append(MusicDownloadVariant(bitrate=bitrate, download_url=url))

        if not downloads:
            return

        # 128k is the balanced default for inline playback.
        by_bitrate = {d.bitrate: d.download_url for d in downloads}
        stream_url = by_bitrate.get("128kbps") or downloads[0].download_url

        artist, title = self._parse_names(html, item.title)
        track = MusicTrack(
            id=f"{item.id}_track",
            title=title,
            artist=artist,
            source_name=self.config.name,
            cover_url=item.poster_url,
            stream_url=stream_url,
            downloads=downloads,
        )
        item.music_tracks = [track]
        item.stream_url = stream_url

    def _parse_names(self, html: str, fallback_title: str) -> tuple[str, str]:
        """Return (artist, title), preferring schema.org MusicRecording over the h1 heading."""
        ld_match = re.search(
            r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        if ld_match:
            try:
                data = json.loads(ld_match.group(1))
            except (json.JSONDecodeError, ValueError):
                data = None
            if isinstance(data, dict) and data.get("name"):
                artist = (data.get("byArtist") or {}).get("name") or ""
                return (artist.strip() or "Unknown Artist", str(data["name"]).strip())

        h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL | re.IGNORECASE)
        if h1_match:
            text = re.sub(r"<[^>]+>", " ", h1_match.group(1))
            # "دانلود آهنگ <artist> به نام <title>" -> split on the Persian marker.
            parts = re.split(r"به نام", text, maxsplit=1)
            if len(parts) == 2:
                artist = re.sub(r"دانلود آهنگ", "", parts[0]).strip()
                title = parts[1].strip()
                if artist and title:
                    return (artist, title)

        return ("Unknown Artist", fallback_title)
