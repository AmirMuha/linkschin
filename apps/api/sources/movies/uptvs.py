"""UpTVs scraper plugin for movies and series."""

from __future__ import annotations

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

DEFAULT_BASE_URL = "https://www.uptvs.com"

# Persian markers only. A bare 'اشتراک' means "share" (اشتراک گذاری) on these portals,
# so only the 'ویژه' (special) form counts as a paywall.
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


class UpTVsPlugin:
    """UpTVs movie scraper plugin."""

    def __init__(self, config: SourceConfig | None = None):
        self.config = config or SourceConfig(
            id="uptvs",
            name="UpTVs",
            category=Category.MOVIES,
            base_urls=[DEFAULT_BASE_URL],
            enabled=True,
            timeout_seconds=7.0,
            access_tier=SourceAccessTier.FREE,
        )

    @property
    def base_url(self) -> str:
        return self.config.primary_base_url or DEFAULT_BASE_URL

    async def search(
        self,
        query: SearchQuery,
        client: AsyncHttpClient,
    ) -> list[MediaItem]:
        """Search UpTVs for movie titles."""
        search_term = query.normalized_query or query.raw_query
        encoded_term = quote(search_term)
        search_url = f"{self.base_url}/?s={encoded_term}"

        try:
            resp = await client.get(search_url, timeout=self.config.timeout_seconds)
            if resp.status_code != 200 or is_parked_page(resp.text):
                logger.warning("UpTVs search returned %s or parked page", resp.status_code)
                return []
            return self.parse_search_results(resp.text)
        except Exception as e:
            logger.error("UpTVs search failed: %s", e)
            return []

    def parse_search_results(self, html: str) -> list[MediaItem]:
        """Extract media items from search results HTML."""
        items: list[MediaItem] = []
        pattern = re.compile(
            r'<a[^>]+href=[\"\'](https?://[^\"\'\s]+/contents/[^\"\']+)[\"\'][^>]*title=[\"\']([^\"\']+)[\"\']',
            re.IGNORECASE,
        )

        seen_urls: set[str] = set()

        for match in pattern.finditer(html):
            raw_url = match.group(1).strip()
            raw_title = match.group(2).strip()
            clean_title = re.sub(r"<[^>]+>", "", raw_title).strip()

            if not raw_url or raw_url in seen_urls or is_ad_or_shortener_url(raw_url):
                continue

            seen_urls.add(raw_url)

            # Year extraction from title or URL (e.g. 2024, 2025, 2026)
            year_match = re.search(r"\b(20[12]\d)\b", clean_title) or re.search(r"-(20[12]\d)\.html", raw_url)
            release_year = int(year_match.group(1)) if year_match else None

            # The IMDb score lives inside the card, after this link's own markup, so scope the
            # lookup to the enclosing card rather than the whole page.
            imdb_rating = self._parse_imdb(html[match.end():match.end() + 4000])

            item_id = f"uptvs_{re.sub(r'[^a-zA-Z0-9]', '_', clean_title)[:40]}"
            items.append(
                MediaItem(
                    id=item_id,
                    title=clean_title,
                    category=Category.MOVIES,
                    source_id=self.config.id,
                    page_url=clean_absolute_url(self.base_url, raw_url),
                    release_year=release_year,
                    imdb_rating=imdb_rating,
                    source_access_tier=self.config.access_tier,
                )
            )

        return items

    @staticmethod
    def _parse_imdb(chunk: str) -> float | None:
        """Pull UpTVs' 'N /10' card score. JSON-LD aggregateRating is a 0-100 site vote."""
        m = re.search(
            r'ficon-imdb[^>]*>\s*</i>\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*10',
            chunk,
            re.IGNORECASE,
        )
        if not m:
            return None
        score = float(m.group(1))
        return round(score, 1) if 0.0 <= score <= 10.0 else None

    async def extract_links(
        self,
        item: MediaItem,
        client: AsyncHttpClient,
    ) -> MediaItem:
        """Fetch movie page and extract direct download links and stream URLs."""
        try:
            resp = await client.get(item.page_url, timeout=self.config.timeout_seconds)
            if resp.status_code == 200 and not is_parked_page(resp.text):
                self.parse_item_page(resp.text, item)
        except Exception as e:
            logger.error("UpTVs link extraction failed for %s: %s", item.page_url, e)

        return item

    def parse_item_page(self, html: str, item: MediaItem) -> None:
        """Parse movie details page for video variants and stream URL."""
        # Extract poster if available
        poster_match = re.search(
            r'<img[^>]+src=[\"\'](https?://[^\s\"\']+(?:jpg|jpeg|png|webp))[\"\'][^>]*class=[\"\'][^\"\']*poster[^\"\']*[\"\']',
            html,
            re.IGNORECASE,
        ) or re.search(
            r'<div[^>]*class=[\"\'][^\"\']*poster[^\"\']*[\"\'][^>]*>\s*<img[^>]+src=[\"\'](https?://[^\s\"\']+)[\"\']',
            html,
            re.IGNORECASE,
        )
        if poster_match:
            item.poster_url = poster_match.group(1).strip()

        # Extract direct download links
        link_pattern = re.compile(
            r'<a\s+[^>]*href=[\"\'](https?://[^\s\"\']+\.(?:mp4|mkv)(?:\?[^\s\"\']*)?)[\"\'][^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )

        variants: list[MovieDownloadVariant] = []
        seen_urls: set[str] = set()

        for match in link_pattern.finditer(html):
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
            elif any(term in (raw_url + " " + raw_label).lower() for term in ("sub", "زیرنویس")):
                audio = "زیرنویس فارسی"

            # ponytail: VIP detection from label/anchor text; no markup says 'premium' outright on uptvs
            is_premium = bool(re.search(r'\bVIP\b|وی\.آی\.پی|اشتراک ویژه|paid|vip', raw_label + " " + raw_url, re.I))

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
            # A page-level badge describes the whole release; a per-link marker still wins.
            page_flag = _censorship_flag(html)
            for v in variants:
                if v.is_censored is None:
                    v.is_censored = page_flag
            item.censorship_status = derive_censorship_status(variants)

        # Extract direct stream URL (opportunistic HTML5 player)
        # UpTVs direct MP4s (like 720p or trailer) can be used as stream_url
        mp4_variants = [v for v in variants if ".mp4" in v.download_url.lower()]
        if mp4_variants:
            # Prefer 720p MP4 for smooth streaming if available, else first MP4
            pref_720 = next((v for v in mp4_variants if "720" in v.quality), mp4_variants[0])
            item.stream_url = pref_720.download_url
