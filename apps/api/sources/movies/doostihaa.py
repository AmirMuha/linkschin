"""Doostihaa scraper plugin for movies and series."""

from __future__ import annotations

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
from sources.base import (
    ACCESS_NEEDS_LOGIN,
    MEDIA_LINK_RE,
    clean_absolute_url,
    is_ad_or_shortener_url,
    is_host,
    is_parked_page,
    iter_links,
    parse_audio_track,
    parse_codec,
    parse_quality,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://www.doostihaa.com"

# hub.irdanlod.ir serves a login-walled SPA for every media path (HTTP 200,
# content-type text/html, body "این لینک در دسترس نیست"). Links there are not
# direct downloads, so they are labelled rather than offered as a plain download.
LOGIN_WALLED_HOST = "hub.irdanlod.ir"


class DoostihaaPlugin:
    """Doostihaa movie scraper plugin."""

    def __init__(self, config: SourceConfig | None = None):
        self.config = config or SourceConfig(
            id="doostihaa",
            name="Doostihaa",
            category=Category.MOVIES,
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
        """Search Doostihaa for movie titles."""
        search_term = query.normalized_query or query.raw_query
        encoded_term = quote(search_term)
        search_url = f"{self.base_url}/?s={encoded_term}"

        try:
            resp = await client.get(search_url, timeout=self.config.timeout_seconds)
            if resp.status_code != 200 or is_parked_page(resp.text):
                logger.warning("Doostihaa search returned %s or parked page", resp.status_code)
                return []
            return self.parse_search_results(resp.text)
        except Exception as e:
            logger.error("Doostihaa search failed: %s", e)
            return []

    def parse_search_results(self, html: str) -> list[MediaItem]:
        """Extract media items from search results HTML."""
        items: list[MediaItem] = []
        article_pattern = re.compile(r'<article[^>]*>(.*?)</article>', re.DOTALL | re.IGNORECASE)

        seen_urls: set[str] = set()

        for art_match in article_pattern.finditer(html):
            art_html = art_match.group(1)

            # Match title and link
            link_match = re.search(
                r'<h2[^>]*class=[\"\'][^\"\']*title[^\"\']*[\"\'][^>]*>\s*<a[^>]+href=[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</a>',
                art_html,
                re.DOTALL | re.IGNORECASE,
            ) or re.search(
                r'<a[^>]+href=[\"\'](https?://[^\"\'\s]+/post/[^\"\']+)[\"\'][^>]*>(.*?)</a>',
                art_html,
                re.DOTALL | re.IGNORECASE,
            )

            if not link_match:
                continue

            raw_url = link_match.group(1).strip()
            raw_title = link_match.group(2).strip()
            clean_title = re.sub(r"<[^>]+>", "", raw_title).strip()
            clean_title = clean_title.replace("&#8211;", "-").replace("&amp;", "&")

            if not raw_url or raw_url in seen_urls or is_ad_or_shortener_url(raw_url):
                continue

            seen_urls.add(raw_url)

            # Extract poster if inside article
            poster_match = re.search(r'<img[^>]+src=[\"\'](https?://[^\s\"\']+\.(?:jpg|jpeg|png|webp))[\"\']', art_html, re.I)
            poster_url = poster_match.group(1).strip() if poster_match else None

            # Year extraction
            year_match = re.search(r"\b(20[12]\d)\b", clean_title) or re.search(r"/(20[12]\d)/", raw_url)
            release_year = int(year_match.group(1)) if year_match else None

            item_id = f"doostihaa_{re.sub(r'[^a-zA-Z0-9]', '_', clean_title)[:40]}"
            items.append(
                MediaItem(
                    id=item_id,
                    title=clean_title,
                    category=Category.MOVIES,
                    source_id=self.config.id,
                    page_url=clean_absolute_url(self.base_url, raw_url),
                    release_year=release_year,
                    poster_url=poster_url,
                )
            )

        return items

    async def extract_links(
        self,
        item: MediaItem,
        client: AsyncHttpClient,
    ) -> MediaItem:
        """Fetch movie details page and extract download links."""
        try:
            resp = await client.get(item.page_url, timeout=self.config.timeout_seconds)
            if resp.status_code == 200 and not is_parked_page(resp.text):
                self.parse_item_page(resp.text, item)
        except Exception as e:
            logger.error("Doostihaa link extraction failed for %s: %s", item.page_url, e)

        return item

    def parse_item_page(self, html: str, item: MediaItem) -> None:
        """Parse movie details page for video variants."""
        # Poster fallback if not found in search
        if not item.poster_url:
            poster_match = re.search(
                r'<img[^>]+src=[\"\'](https?://[^\s\"\']+(?:uploads|img)[^\s\"\']+\.(?:jpg|jpeg|png|webp))[\"\']',
                html,
                re.IGNORECASE,
            )
            if poster_match:
                item.poster_url = poster_match.group(1).strip()

        # Extract direct download links
        variants: list[MovieDownloadVariant] = []
        seen_urls: set[str] = set()

        for link in iter_links(html, MEDIA_LINK_RE):
            clean_url = clean_absolute_url(self.base_url, link.url)

            if not clean_url or clean_url in seen_urls or is_ad_or_shortener_url(clean_url):
                continue

            haystack = link.url + " " + link.label

            seen_urls.add(clean_url)
            variants.append(
                MovieDownloadVariant(
                    id=f"{item.id}_{len(variants)}",
                    quality=parse_quality(haystack),
                    codec=parse_codec(haystack),
                    audio_track=parse_audio_track(haystack),
                    download_url=clean_url,
                    source_name=self.config.name,
                    # hub.irdanlod.ir answers 200 with a login-walled HTML page for every
                    # path. Flag it instead of presenting it as a direct .mkv download.
                    access=ACCESS_NEEDS_LOGIN if is_host(clean_url, LOGIN_WALLED_HOST) else "direct",
                )
            )

        if variants:
            item.movie_variants = variants

        # Direct MP4 stream selection if available
        mp4_variants = [v for v in variants if ".mp4" in v.download_url.lower()]
        if mp4_variants:
            pref_720 = next((v for v in mp4_variants if "720" in v.quality), mp4_variants[0])
            item.stream_url = pref_720.download_url
