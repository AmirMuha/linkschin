"""Doostihaa scraper plugin for movies and series."""

from __future__ import annotations

import html as html_lib
import logging
import re
from urllib.parse import quote

from http_client import AsyncHttpClient
from models import (
    Category,
    CensorshipStatus,
    MediaItem,
    MovieDownloadVariant,
    SearchQuery,
    SourceAccessTier,
    SourceConfig,
)
from sources.base import (
    clean_absolute_url,
    is_ad_or_shortener_url,
    is_parked_page,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://www.doostihaa.com"

# Doostihaa HTML-encodes its Persian body text (&#1575;&#1605;&#1578;...), so every Persian
# match runs against html.unescape() output, never the raw page.
# A bare 'اشتراک' means "share" (اشتراک گذاری) here; only 'ویژه' marks a paywall.
_UNCENSORED_MARKERS = re.compile(r"نسخه\s*کامل|بدون\s*سانسور|uncut")
_CENSORED_MARKERS = re.compile(r"بازبینی\s*شده|سانسور\s*شده|نسخه\s*سانسور")
_VIP_MARKERS = re.compile(r"\bVIP\b|وی\.آی\.پی|اشتراک\s*ویژه", re.IGNORECASE)


def _censorship_flag(text: str) -> bool | None:
    """True/False when a marker is present, None when the source says nothing (never guess)."""
    if _CENSORED_MARKERS.search(text):
        return True
    if _UNCENSORED_MARKERS.search(text):
        return False
    return None


def derive_censorship_status(variants: list[MovieDownloadVariant]) -> CensorshipStatus:
    """Roll per-variant flags up to an item status; unknown stays unknown (spec 007)."""
    flags = {v.is_censored for v in variants if v.is_censored is not None}
    if not flags:
        return CensorshipStatus.UNSPECIFIED
    if len(flags) > 1:
        return CensorshipStatus.MIXED
    return CensorshipStatus.CENSORED if flags.pop() else CensorshipStatus.UNCENSORED


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
            access_tier=SourceAccessTier.FREEMIUM,
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

            # Persian body text is entity-encoded (&#1575;&#1605;&#1578;...), so match
            # against decoded text; the raw block still serves the href/img lookups.
            try:
                decoded_body = html_lib.unescape(art_html)
            except Exception:
                continue

            # Match title and link
            link_match = re.search(
                r'<h2[^>]*class=[\"\'][^\"\']*title[^\"\']*[\"\'][^>]*>\s*<a[^>]+href=[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</a>',
                decoded_body,
                re.DOTALL | re.IGNORECASE,
            ) or re.search(
                r'<a[^>]+href=[\"\'](https?://[^\"\'\s]+/post/[^\"\']+)[\"\'][^>]*>(.*?)</a>',
                decoded_body,
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

            # IMDb score lives in the article body. JSON-LD aggregateRating here is a
            # 1-5 site-user vote, so it is deliberately not consulted.
            imdb_rating = self._parse_imdb(decoded_body)

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
                    imdb_rating=imdb_rating,
                    source_access_tier=self.config.access_tier,
                )
            )

        return items

    @staticmethod
    def _parse_imdb(body: str) -> float | None:
        """Read 'امتیاز: N از 10' (or the /10 form) from a decoded article body."""
        m = re.search(r"امتیاز[^0-9]{0,12}([0-9]+(?:\.[0-9]+)?)", body)
        if not m:
            return None
        score = float(m.group(1))
        return round(score, 1) if 0.0 <= score <= 10.0 else None

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
        # Persian text is entity-encoded, so decode before matching markers.
        try:
            decoded = html_lib.unescape(html)
        except Exception:
            decoded = html

        # Poster fallback if not found in search
        if not item.poster_url:
            poster_match = re.search(
                r'<img[^>]+src=[\"\'](https?://[^\s\"\']+(?:uploads|img)[^\s\"\']+\.(?:jpg|jpeg|png|webp))[\"\']',
                html,
                re.IGNORECASE,
            )
            if poster_match:
                item.poster_url = poster_match.group(1).strip()

        # Extract direct download links. Run against the decoded page so the anchor
        # labels (Persian, entity-encoded upstream) are readable for marker matching.
        link_pattern = re.compile(
            r'<a\s+[^>]*href=[\"\'](https?://[^\s\"\']+\.(?:mp4|mkv)(?:\?[^\s\"\']*)?)[\"\'][^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )

        variants: list[MovieDownloadVariant] = []
        seen_urls: set[str] = set()

        for match in link_pattern.finditer(decoded):
            raw_url = match.group(1).strip()
            raw_label = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            clean_url = clean_absolute_url(self.base_url, raw_url)

            if not clean_url or clean_url in seen_urls or is_ad_or_shortener_url(clean_url):
                continue

            # Parse quality
            quality = "1080p"
            quality_match = re.search(r"\b(2160p|4k|1080p|720p|480p)\b", raw_url + " " + raw_label, re.IGNORECASE)
            if quality_match:
                quality = quality_match.group(1).lower()

            # Parse codec
            codec = "x264"
            codec_match = re.search(r"\b(x265|hevc|10bit|x264)\b", raw_url + " " + raw_label, re.IGNORECASE)
            if codec_match:
                codec = codec_match.group(1).lower()

            # Parse audio / subtitle
            audio = "زبان اصلی"
            if any(term in (raw_url + " " + raw_label).lower() for term in ("dubbed", "دوبله")):
                audio = "دوبله فارسی"
            elif any(term in (raw_url + " " + raw_label).lower() for term in ("sub", "subbed", "زیرنویس")):
                audio = "زیرنویس فارسی"

            # ponytail: VIP is detected from link text/URL; doostihaa gates HD behind
            # membership in the live site but the recorded fixture has no such row.
            is_premium = bool(_VIP_MARKERS.search(raw_label + " " + raw_url))

            seen_urls.add(clean_url)
            variants.append(
                MovieDownloadVariant(
                    id=f"{item.id}_{quality}_{codec}_{len(variants)}",
                    quality=quality,
                    codec=codec,
                    audio_track=audio,
                    download_url=clean_url,
                    source_name=self.config.name,
                    is_censored=_censorship_flag(raw_label + " " + raw_url),
                    is_premium=is_premium,
                )
            )

        if variants:
            item.movie_variants = variants
            # A page-level tag ("نسخه سانسور شده Batman…") describes the whole release, so
            # it seeds every variant; a per-link marker still wins where present.
            page_flag = _censorship_flag(decoded)
            for v in variants:
                if v.is_censored is None:
                    v.is_censored = page_flag
            item.censorship_status = derive_censorship_status(variants)

        # Direct MP4 stream selection if available
        mp4_variants = [v for v in variants if ".mp4" in v.download_url.lower()]
        if mp4_variants:
            pref_720 = next((v for v in mp4_variants if "720" in v.quality), mp4_variants[0])
            item.stream_url = pref_720.download_url
