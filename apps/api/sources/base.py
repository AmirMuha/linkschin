"""Source plugin base protocol and shared parsing helpers."""

from __future__ import annotations

import html
import re
from typing import Mapping, Protocol, runtime_checkable
from urllib.parse import unquote, urljoin, urlparse

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


def unescape_entities(text: str) -> str:
    """Decode HTML entities; WordPress search markup is heavily entity-encoded."""
    return html.unescape(text)


def strip_tags(text: str) -> str:
    """Flatten an HTML fragment to readable text."""
    return re.sub(r"\s+", " ", unescape_entities(re.sub(r"<[^>]+>", " ", text))).strip()


# The two Persian idioms every Iranian music portal uses: "به نام <title>" and
# "دانلود آهنگ <title> از <artist>". Anything else falls back to the last word.
_TITLE_MARKER = re.compile(r"به نام")
# Trailing version/remix tags are not the song title: "… + ریمیکس", "… (ریمیکس)".
_VERSION_TAG = re.compile(r"[\s(+–-]*(ریمیکس|ریمیس|دمو|نسخه\s*\S*|version|remix|mix)\s*\)?\s*$",
                          re.IGNORECASE)


def split_track_names(title: str) -> tuple[str, str]:
    """Return (artist, title) from a Persian "دانلود آهنگ …" heading.

    "به نام <artist> <title>" is the only unambiguous marker; the bare " از "
    fallback is off, because "فرهاد وای از دستت هوش مصنوعی" is a song title that
    contains it. Sites whose verified markup proves an artist keep parsing it
    themselves.
    """
    text = _VERSION_TAG.sub("", strip_tags(title)).strip()
    if m := _TITLE_MARKER.search(text):
        return _clean_name(text[: m.start()]), _clean_name(text[m.end():])
    return "", _clean_name(text)


def _clean_name(text: str) -> str:
    """Drop the page's boilerplate prefix ("دانلود آهنگ جدید", "دانلود آهنگ")."""
    return _DOWNLOAD_NOISE.sub("", strip_tags(text)).strip(" -–:")


_DOWNLOAD_NOISE = re.compile(r"^دانلود\s+(?:آهنگ|موزیک|آهنگ جدید|موزیک جدید)\s*", re.IGNORECASE)

# Anchor attributes of a WordPress permalink, in any of the order WP themes emit.
_BOOKMARK_HREF = re.compile(r"""href=["']([^"']+)["']""", re.IGNORECASE)
_BOOKMARK_TITLE = re.compile(r"""title=["']([^"']*)["']""", re.IGNORECASE)
_IMG_SRC = re.compile(r"""(?:\bdata-src|\bsrc)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


def wp_cards(html: str, card_class: str) -> list[str]:
    """Split a WordPress listing page into its per-post card blocks.

    Every verified portal wraps results in a themed ``<article class="…">``; the
    class is the only thing that differs between sites.
    """
    return html.split(f'<article class="{card_class}"')[1:]


def wp_card_link(block: str, base_url: str) -> tuple[str, str]:
    """Return (page_url, title) for a card's ``rel="bookmark"`` permalink.

    The anchor's ``title`` attribute carries the full "دانلود آهنگ <artist> …"
    heading; some themes render only a generic "دانلود آهنگ" as the link text.
    """
    m = re.search(r"<a[^>]*rel=[\"']bookmark[\"'][^>]*>", block, re.IGNORECASE)
    if m is None:
        # Theme puts rel=bookmark before href; retry on the anchor body.
        m = re.search(r"""<a[^>]*href=["'][^"']+["'][^>]*rel=["']bookmark["'][^>]*>""",
                      block, re.IGNORECASE)
        if m is None:
            return "", ""
    href = _BOOKMARK_HREF.search(m.group(0))
    if href is None:
        return "", ""
    url = clean_absolute_url(base_url, href.group(1))
    if not url or is_ad_or_shortener_url(url):
        return "", ""
    anchor_body = block[m.end():]
    title = _BOOKMARK_TITLE.search(m.group(0))
    if title is None:
        # No title attribute on the anchor: use the link text up to the close tag.
        title = re.search(r"title=[\"']([^\"']*)[\"']", block, re.IGNORECASE)
    return url, strip_tags(title.group(1)) if title else strip_tags(anchor_body[:200])


def wp_card_poster(block: str, base_url: str) -> str | None:
    """Return the card's cover image, skipping lazy-load data: placeholders."""
    for src in _IMG_SRC.findall(block):
        if src.startswith("data:"):
            continue
        candidate = clean_absolute_url(base_url, src.strip())
        if candidate and not is_ad_or_shortener_url(candidate):
            return candidate
    return None


def mp3_bitrate(url: str, label: str = "") -> str:
    """Infer a bitrate label from a download URL/filename or its link text.

    Iranian WordPress music portals label quality in the filename
    (``-128.mp3`` = 128kbps, ``-64.mp3`` = 64kbps, ``%20128.mp3`` = 128kbps, a bare
    ``.mp3`` = 320kbps) and/or in the anchor text ("با کیفیت 320"). The URL is
    percent-decoded first: the quality marker is routinely percent-encoded.
    """
    haystack = f"{unquote(url)} {label}"
    for bits, match in (
        ("128kbps", r"(?<!\d)128(?!\d)|۱۲۸"),
        ("64kbps", r"(?<!\d)64(?!\d)|۶۴"),
        ("320kbps", r"(?<!\d)320(?!\d)|۳۲۰"),
    ):
        if re.search(match, haystack):
            return bits
    return "320kbps"


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
