"""Source plugin base protocol and shared parsing helpers."""

from __future__ import annotations

import re
from typing import Mapping, Protocol, runtime_checkable
from urllib.parse import urljoin, urlparse

from http_client import AsyncHttpClient
from models import MediaItem, SearchQuery, SourceConfig


# Known ad shortener or referral domains to reject per Link Hygiene rule
AD_SHORTENER_DOMAINS = {
    "adf.ly", "sh.st", "ouo.io", "bit.ly", "tinyurl.com",
    "adclick", "popads", "lander", "clickbank",
}

# Signatures indicating domain parking, ad landing pages, or expired domains
PARKED_PAGE_SIGNATURES = [
    r"/lander",
    r"buy this domain",
    r"domain is for sale",
    r"parked-domain",
    r"sedoparking",
    r"namecheap\.com/domains/marketplace",
]

# Persian to English digit mapping
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def is_ad_or_shortener_url(url: str) -> bool:
    """Return True if URL matches known ad or intermediate referral patterns."""
    if not url:
        return True
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    for ad_domain in AD_SHORTENER_DOMAINS:
        if ad_domain in host or ad_domain in parsed.path.lower():
            return True
    return False


def is_parked_page(html: str) -> bool:
    """Check if HTML content indicates an ad parking page instead of real content."""
    if not html:
        return True
    for sig in PARKED_PAGE_SIGNATURES:
        if re.search(sig, html, re.I):
            return True
    return False


def normalize_digits(text: str) -> str:
    """Convert Persian/Arabic digits to ASCII digits."""
    return text.translate(PERSIAN_DIGITS)


def parse_part_number(label: str) -> int | None:
    """
    Extract integer part number from text.
    Handles 'Part 1', 'Part02', 'پارت ۱', 'part-3', 'part4', etc.
    """
    if not label:
        return None
    normalized = normalize_digits(label)
    match = re.search(r"(?:part|پارت|قسمت)[^\d]*(\d+)", normalized, re.I)
    if match:
        return int(match.group(1))
    return None


def extract_archive_password(text: str) -> str:
    """
    Extract archive extraction password from text.
    Looks for 'رمز فایل: ...', 'password: ...', 'رمز: ...'.
    """
    if not text:
        return ""
    patterns = [
        r"(?:رمز فایل|رمز عبور|پسورد|password|pass)\s*[:：\-]\s*([a-zA-Z0-9\.\-_]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            found = match.group(1) if match.groups() else match.group(0)
            cleaned = found.strip().rstrip(".,;:")
            # Filter out non-passwords like "Copy"
            if cleaned.lower() not in ("copy", "paste", "repair", "click", "download"):
                return cleaned
    return ""


def clean_absolute_url(base_url: str, link: str) -> str:
    """Ensure link is an absolute HTTP/HTTPS URL joined to base_url."""
    if not link:
        return ""
    joined = urljoin(base_url, link.strip())
    parsed = urlparse(joined)
    if parsed.scheme.lower() not in ("http", "https"):
        return ""
    return joined


def is_directly_playable(status_code: int, headers: Mapping[str, str] | None) -> bool:
    """
    Pure verdict from a HEAD response.
    Requires: status < 400, audio/video Content-Type, and permissive CORS.
    """
    if status_code >= 400:
        return False
    h = {k.lower(): v for k, v in (headers or {}).items()}
    mime = h.get("content-type", "").split(";")[0].strip().lower()
    if not (mime.startswith("audio/") or mime.startswith("video/")):
        return False
    cors = h.get("access-control-allow-origin", "").strip()
    return bool(cors)


async def validate_stream_url(url: str, client: AsyncHttpClient) -> bool:
    """Validate whether direct stream URL is directly playable in browser."""
    if not url or is_ad_or_shortener_url(url):
        return False
    try:
        resp = await client.head(url)
    except Exception:
        return False
    return is_directly_playable(resp.status_code, resp.headers)


@runtime_checkable
class SourcePlugin(Protocol):
    """Protocol that every category source plugin must implement."""

    config: SourceConfig

    async def search(
        self,
        query: SearchQuery,
        client: AsyncHttpClient,
    ) -> list[MediaItem]:
        """
        Search the upstream source portal for the query.
        Returns a list of MediaItem cards with summary metadata.
        Must NOT raise uncaught network exceptions (catch and return []).
        """
        ...

    async def extract_links(
        self,
        item: MediaItem,
        client: AsyncHttpClient,
    ) -> MediaItem:
        """
        Extract direct download links and streaming URLs for a specific media item.
        Populates item.movie_variants, item.game_releases, or item.music_tracks.
        Returns the enriched MediaItem.
        """
        ...
