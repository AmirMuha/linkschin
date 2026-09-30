"""Source plugin base protocol and shared parsing helpers."""

from __future__ import annotations

import html
import re
from typing import Iterator, Mapping, NamedTuple, Protocol, runtime_checkable
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


def is_host(url: str, domain: str) -> bool:
    """True when `url` is served by `domain` (or a subdomain of it).

    Compares hosts, not string prefixes: a URL begins with its scheme, so
    `url.startswith("cdn.example.com")` is never true.
    """
    host = (urlparse(url).hostname or "").lower()
    domain = domain.lower()
    return host == domain or host.endswith("." + domain)


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


def unescape_html(text: str) -> str:
    """Decode HTML entities and normalise the space-like characters portals emit.

    `&nbsp;` decodes to U+00A0 and ZWNJ to U+200C, neither of which equals a plain
    space in a substring match - so a title split by one of them would silently fail
    every keyword check and search normalisation alike.
    """
    return html.unescape(text).translate(_SPACE_CHARS)


_SPACE_CHARS = {ord(" "): " ", ord(" "): " ", ord(" "): " ", ord("‌"): " ",
                ord("‍"): "", ord("﻿"): ""}


# `(?<!\d)` rather than `\b`: portals join filename tokens with underscores, and `_`
# is a word character, so `\b720p\b` never matches "..._720p_UPTV.co.mp4".
QUALITY_RE = re.compile(r"(?<!\d)(2160p|1440p|1080p|720p|480p|360p)", re.IGNORECASE)
# CDNs that name streams positionally rather than by suffix: "3080511-0-720.mp4".
BARE_RESOLUTION_RE = re.compile(r"[-_.](\d{3,4})p?\.(?:mp4|mkv|webm)\b", re.IGNORECASE)
CODEC_RE = re.compile(r"\b(x265|hevc|h\.?265|10bit|x264|avc)\b", re.IGNORECASE)


def parse_quality(*parts: str) -> str:
    """Best-effort resolution label, or "" when the source never states one.

    Deliberately returns "" rather than a guess: a made-up "1080p" is worse than a
    blank, because the UI presents it as fact next to the codec badge.
    """
    text = " ".join(parts)
    match = QUALITY_RE.search(text)
    if match:
        return match.group(1).lower()
    match = BARE_RESOLUTION_RE.search(text)
    if match:
        return f"{match.group(1)}p"
    return ""


def parse_codec(*parts: str) -> str:
    """Best-effort codec label, or "" when the source never states one."""
    match = CODEC_RE.search(" ".join(parts))
    return match.group(1).lower().replace(".", "") if match else ""


# Access states for a direct-download link. "direct" is the only one the app may
# present as a plain download; "needs_login" means the host answers with an
# interstitial page instead of the file.
ACCESS_DIRECT = "direct"
ACCESS_NEEDS_LOGIN = "needs_login"

DUBBED_TERMS = ("dubbed", "dub", "دوبله", "فارسی")
SUBTITLED_TERMS = ("subbed", "sub", "زیرنویس")


def parse_audio_track(*parts: str) -> str:
    """Classify a variant's audio/subtitle track from its filename or link text."""
    text = " ".join(parts).lower()
    if any(term in text for term in DUBBED_TERMS):
        return "دوبله فارسی"
    if any(term in text for term in SUBTITLED_TERMS):
        return "زیرنویس فارسی"
    return "زبان اصلی"


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


# Shared anchor patterns for downloadable media. Live portals write the href with
# stray whitespace before the closing quote (`href="....part1.rar "`) on every part
# except the last, so a pattern that demands the extension touch the quote silently
# drops all but the final link. The `\s*` and the `<>` exclusion are both load-bearing:
# the latter stops a lazy match from swallowing the next attribute.
def href_link_re(*extensions: str) -> re.Pattern[str]:
    """Anchor pattern matching direct-download hrefs for the given file extensions."""
    exts = "|".join(extensions)
    return re.compile(
        rf'<a\b[^>]*?href=[\"\']([^\"\'<>]*?\.(?:{exts})(?:\?[^\"\'<>]*)?)\s*[\"\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )


ARCHIVE_LINK_RE = href_link_re("rar", "zip", "7z", "bin", "iso")
SELF_EXTRACTING_LINK_RE = href_link_re("rar", "zip", "7z", "bin", "iso", "exe")

MEDIA_LINK_RE = re.compile(
    r'<a\b[^>]*?href=[\"\'](https?://[^\"\'<>\s]+?\.(?:mp4|mkv)(?:\?[^\"\'<>\s]*)?)\s*[\"\'][^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)

# Trailing volume marker of a split archive: "game.part12.rar" -> "game".
PART_SUFFIX_RE = re.compile(r"[._-]?part[-_. ]?\d+\s*$", re.IGNORECASE)


def archive_family(url: str) -> str:
    """Filename stem minus any `.partN` marker, identifying one archive set.

    A post can ship two archives that both number their parts from 1 (e.g. an exFAT
    image and a PKG). Grouping on this stem keeps each sequence strictly 1..N instead
    of merging them into one list with duplicate part numbers.
    """
    name = urlparse(url).path.rsplit("/", 1)[-1]
    stem = name.rsplit(".", 1)[0] if "." in name else name
    return PART_SUFFIX_RE.sub("", stem).strip() or stem


# Post classification from the title alone. The game portals also publish soundtracks
# and plain software, and the title is the only signal available before the (much
# slower) item fetch.
_SOUNDTRACK_TERMS = ("موسیقی متن", "موسیقی", "موزیک", "آلبوم", "OST", "soundtrack")
# Not games, and not media at all: emulators, storefronts, recovery/office tools.
# `شبیه ساز` ("simulator") is NOT here on its own -- it is a substring of بازی شبیه ساز
# ("simulation game"), which titles Euro Truck Simulator 2. The emulator posts name
# their emulated platform instead, so those two phrasings catch them without the clash.
_SOFTWARE_TERMS = (
    "microsoft store", "بلو استکس", "bluestacks", "شبیه ساز اندروید", "اندروید شبیه ساز",
    "emulator",
    "بازیابی اطلاعات", "format recovery", "anti virus", "آنتی ویروس",
    "مرورگر", "browser", "دانلود برنامه", "نرم افزار",
)


def classify_post(title: str) -> str | None:
    """Return "game", "music", or None when the post is not media worth indexing.

    `ost` is deliberately not a standalone term: it substring-matches "Costs",
    dropping real games. "موسیقی متن" and friends carry the same idea without the
    collision, so the soundtrack list stays title-shaped.
    """
    low = title.lower()
    if any(term in low for term in _SOFTWARE_TERMS):
        return None
    if any(term in low for term in _SOUNDTRACK_TERMS):
        return "music"
    return "game"


def is_game_post(title: str, post_url: str) -> bool:
    """True when a post filed by a games source really is a game.

    Title markers alone cannot decide this: Downloadha's GTA OST is titled "دانلود
    موسیقی متن بازی GTA Online ..." and so *contains* the game marker. Only the URL
    section separates it from a real game post, so that is the gate -- with a
    carve-out for Android games, which the site files under /mobile/ too.
    """
    if classify_post(title) != "game":
        return False
    sections = [p for p in urlparse(post_url).path.split("/") if p]
    section = sections[0].lower() if sections else ""
    if section == "game":
        return True
    return section == "mobile" and "بازی" in title


class ExtractedLink(NamedTuple):
    """One anchor href plus its visible text, tags stripped."""

    url: str
    label: str


def iter_links(html: str, pattern: re.Pattern[str]) -> Iterator[ExtractedLink]:
    """Yield (href, tag-stripped anchor text) for every match, whitespace-trimmed."""
    for match in pattern.finditer(html):
        yield ExtractedLink(match.group(1).strip(), re.sub(r"<[^>]+>", "", match.group(2)).strip())


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
