"""Base movie scraper plugin with standard search and item extraction."""

from __future__ import annotations

import html as html_lib
import logging
import re
from urllib.parse import quote

from http_client import AsyncHttpClient
from models import (
    Category,
    MediaItem,
    MovieDownloadVariant,
    SearchQuery,
    SourceConfig,
)
from sources.base import clean_absolute_url, is_ad_or_shortener_url, is_parked_page

logger = logging.getLogger(__name__)


def extract_movie_variants_from_html(
    html: str,
    source_name: str,
    base_url: str = "",
) -> list[MovieDownloadVariant]:
    """Extract .mp4 and .mkv download links from item page HTML."""
    variants: list[MovieDownloadVariant] = []
    link_pattern = re.compile(
        r'<a[^>]+href=[\"\']([^\"\']+\.(?:mp4|mkv)(?:\?[^\"\']*)?)[\"\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    seen_urls: set[str] = set()

    for match in link_pattern.finditer(html):
        raw_url = match.group(1).strip()
        link_text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        abs_url = clean_absolute_url(base_url, raw_url) if base_url else raw_url
        if not abs_url or abs_url in seen_urls or is_ad_or_shortener_url(abs_url):
            continue
        seen_urls.add(abs_url)

        # Detect quality
        quality_match = re.search(r"\b(1080p|720p|480p|4k|2160p)\b", f"{abs_url} {link_text}", re.I)
        quality = quality_match.group(1).lower() if quality_match else "720p"

        # Detect codec
        codec = "x265" if "x265" in abs_url.lower() or "hevc" in abs_url.lower() else "x264"

        # Audio track
        if "دوبله" in link_text or "dubbed" in abs_url.lower():
            audio = "دوبله فارسی"
        elif "زیرنویس" in link_text or "sub" in abs_url.lower():
            audio = "زیرنویس فارسی"
        else:
            audio = "اصلی"

        # File size
        size_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:MB|مگابایت|گیگابایت|GB)", link_text, re.I)
        file_size_mb = float(size_match.group(1)) if size_match else None
        if size_match and ("gb" in size_match.group(0).lower() or "گیگابایت" in size_match.group(0)):
            file_size_mb = (file_size_mb or 0) * 1024.0

        variants.append(
            MovieDownloadVariant(
                id=f"{source_name.lower()}-{len(variants) + 1}",
                quality=quality,
                codec=codec,
                audio_track=audio,
                download_url=abs_url,
                file_size_mb=file_size_mb,
                source_name=source_name,
            )
        )

    return variants


class BaseMoviePlugin:
    """Base scraper plugin for movies and series."""

    DEFAULT_BASE_URL: str = ""
    SOURCE_ID: str = ""
    SOURCE_NAME: str = ""
    PROVIDES_DOWNLOADS: bool = True
    SEARCH_PATH: str = "/?s={query}"
    ITEM_URL_SUBSTRING: str = ""

    def __init__(self, config: SourceConfig | None = None):
        self.config = config or SourceConfig(
            id=self.SOURCE_ID,
            name=self.SOURCE_NAME,
            category=Category.MOVIES,
            base_urls=[self.DEFAULT_BASE_URL] if self.DEFAULT_BASE_URL else [],
            enabled=True,
            provides_downloads=self.PROVIDES_DOWNLOADS,
            timeout_seconds=7.0,
        )

    @property
    def base_url(self) -> str:
        return self.config.primary_base_url or self.DEFAULT_BASE_URL

    def build_search_url(self, search_term: str) -> str:
        encoded = quote(search_term)
        path = self.SEARCH_PATH.format(query=encoded)
        return clean_absolute_url(self.base_url, path)

    async def search(self, query: SearchQuery, client: AsyncHttpClient) -> list[MediaItem]:
        term = query.normalized_query or query.raw_query
        search_url = self.build_search_url(term)
        try:
            resp = await client.get(search_url, timeout=self.config.timeout_seconds)
            if resp.status_code != 200 or is_parked_page(resp.text):
                return []
            return self.parse_search_results(resp.text)
        except Exception as e:
            logger.error("%s search failed: %s", self.config.name, e)
            return []

    def parse_search_results(self, html: str) -> list[MediaItem]:
        """Extract media items from search results HTML."""
        items: list[MediaItem] = []
        seen_urls: set[str] = set()

        # Strip <style>/<script> first: emotion-CSS sites (filmnet) inline a
        # <style> inside every card, and a naive strip-tags yields CSS as titles.
        stripped = re.sub(
            r"<(?:style|script|noscript)\b[^>]*>.*?</(?:style|script|noscript)>",
            "",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )

        block_pattern = re.compile(
            r'<(?:article|div)[^>]*class=[\"\'][^\"\']*(?:item|post|movie|box|card|content|video)[^\"\']*[\"\'][^>]*>(.*?)</(?:article|div)>',
            re.DOTALL | re.IGNORECASE,
        )
        blocks = list(block_pattern.finditer(stripped))
        content_blocks = [m.group(1) for m in blocks] if blocks else [stripped]

        for block in content_blocks:
            # Find candidate links
            link_matches = re.finditer(
                r'<a[^>]+href=[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</a>',
                block,
                re.DOTALL | re.IGNORECASE,
            )
            for link_match in link_matches:
                raw_url = link_match.group(1).strip()
                raw_title = link_match.group(2).strip()
                clean_title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw_title)).strip()
                clean_title = html_lib.unescape(clean_title)

                if not clean_title:
                    title_attr = re.search(r'title=[\"\']([^\"\']+)[\"\']', link_match.group(0), re.I)
                    if title_attr:
                        clean_title = html_lib.unescape(title_attr.group(1).strip())

                if not clean_title or not raw_url:
                    continue

                if self.ITEM_URL_SUBSTRING and self.ITEM_URL_SUBSTRING not in raw_url:
                    continue

                if any(p in raw_url.lower() for p in ("/category/", "/tag/", "/feed", "/wp-admin", "/page/")):
                    continue

                abs_url = clean_absolute_url(self.base_url, raw_url)
                if not abs_url or abs_url in seen_urls or is_ad_or_shortener_url(abs_url):
                    continue
                seen_urls.add(abs_url)

                poster_match = re.search(
                    r'<img[^>]+src=[\"\']([^\"\'\s]+\.(?:jpg|jpeg|png|webp)[^\"\'\s]*)[\"\']',
                    block,
                    re.I,
                )
                poster_url = clean_absolute_url(self.base_url, poster_match.group(1)) if poster_match else None

                year_match = re.search(r"\b(20[12]\d)\b", f"{clean_title} {abs_url}")
                release_year = int(year_match.group(1)) if year_match else None

                item_id = f"{self.config.id}_{re.sub(r'[^a-zA-Z0-9]', '_', clean_title)[:40]}"
                watch_url = abs_url if not self.config.provides_downloads else None

                items.append(
                    MediaItem(
                        id=item_id,
                        title=clean_title,
                        category=Category.MOVIES,
                        source_id=self.config.id,
                        page_url=abs_url,
                        poster_url=poster_url,
                        release_year=release_year,
                        watch_url=watch_url,
                        movie_variants=[],
                    )
                )

        return items

    def parse_item_page(self, html: str, target: MediaItem) -> None:
        """Extract links into target MediaItem."""
        if not self.config.provides_downloads:
            target.watch_url = target.watch_url or target.page_url
            target.movie_variants = []
            target.stream_url = None
            return

        variants = extract_movie_variants_from_html(html, self.config.name, self.base_url)
        target.movie_variants = variants
        mp4_vars = [v for v in variants if ".mp4" in v.download_url.lower()]
        target.stream_url = mp4_vars[0].download_url if mp4_vars else (variants[0].download_url if variants else None)

    async def extract_links(self, item: MediaItem, client: AsyncHttpClient) -> MediaItem:
        if not self.config.provides_downloads:
            item.watch_url = item.watch_url or item.page_url
            item.movie_variants = []
            item.stream_url = None
            return item

        try:
            resp = await client.get(item.page_url, timeout=self.config.timeout_seconds)
            if resp.status_code == 200 and not is_parked_page(resp.text):
                self.parse_item_page(resp.text, item)
        except Exception as e:
            logger.error("%s extract_links failed: %s", self.config.name, e)
        return item
