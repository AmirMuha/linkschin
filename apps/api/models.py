"""Domain models for Iranian Multi-Media Direct Link Aggregator."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from urllib.parse import urlparse


class Category(str, Enum):
    """Media domain category."""
    MOVIES = "movies"
    GAMES = "games"
    MUSIC = "music"


class SourceKind(str, Enum):
    """Whether a source resolves playable media or is a link-out reference."""
    FULL = "full"
    REFERENCE = "reference"


def validate_media_url(url: str) -> str:
    """Ensure URL strictly adheres to http or https scheme."""
    if not url:
        raise ValueError("URL cannot be empty")
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Only http and https allowed.")
    if not parsed.netloc:
        raise ValueError(f"Invalid URL '{url}'. Missing network location (host).")
    return url.strip()


@dataclass(slots=True)
class SourceConfig:
    """Configuration for an upstream Iranian website scraper."""
    id: str
    name: str
    category: Category
    base_urls: list[str] = field(default_factory=list)
    enabled: bool = True
    timeout_seconds: float = 7.0
    # Default FULL keeps every pre-006 SourceConfig(...) call site working unchanged (FR-028).
    kind: SourceKind = SourceKind.FULL

    @property
    def primary_base_url(self) -> str:
        return self.base_urls[0] if self.base_urls else ""

    @property
    def is_reference(self) -> bool:
        return self.kind is SourceKind.REFERENCE


@dataclass(slots=True)
class SearchQuery:
    """Incoming search request with normalized terms."""
    raw_query: str
    normalized_query: str
    category: Category
    extracted_year: int | None = None


@dataclass(slots=True)
class MovieDownloadVariant:
    """Movie/series download file variant."""
    id: str
    quality: str
    codec: str
    audio_track: str
    download_url: str
    file_size_mb: float | None = None
    source_name: str = ""

    def __post_init__(self):
        validate_media_url(self.download_url)


@dataclass(slots=True)
class GamePartLink:
    """Individual archive part link for multi-part game downloads."""
    part_number: int
    part_label: str
    download_url: str
    file_size: str | None = None

    def __post_init__(self):
        validate_media_url(self.download_url)
        if self.part_number < 1:
            raise ValueError(f"Part number must be >= 1, got {self.part_number}")


@dataclass(slots=True)
class GameRelease:
    """Game release package (e.g. FitGirl Repack, Scene ISO)."""
    id: str
    source_name: str
    release_group: str = ""
    version: str = ""
    total_size: str = ""
    archive_password: str = ""
    parts: list[GamePartLink] = field(default_factory=list)
    has_missing_parts: bool = False
    missing_part_numbers: list[int] = field(default_factory=list)

    def __post_init__(self):
        self.sort_and_validate_parts()

    def sort_and_validate_parts(self) -> None:
        """Sort parts ascending by part_number and detect non-consecutive gaps."""
        if not self.parts:
            self.has_missing_parts = False
            self.missing_part_numbers = []
            return

        self.parts.sort(key=lambda p: p.part_number)
        expected = 1
        missing: list[int] = []
        for part in self.parts:
            while expected < part.part_number:
                missing.append(expected)
                expected += 1
            expected = part.part_number + 1

        self.missing_part_numbers = missing
        self.has_missing_parts = len(missing) > 0


@dataclass(slots=True)
class MusicDownloadVariant:
    """Audio quality download option."""
    bitrate: str
    download_url: str
    file_size: str | None = None

    def __post_init__(self):
        validate_media_url(self.download_url)


@dataclass(slots=True)
class MusicTrack:
    """Music single or album track."""
    id: str
    title: str
    artist: str
    source_name: str
    album: str | None = None
    cover_url: str | None = None
    stream_url: str | None = None
    downloads: list[MusicDownloadVariant] = field(default_factory=list)

    def __post_init__(self):
        if self.stream_url:
            validate_media_url(self.stream_url)
        if self.cover_url:
            validate_media_url(self.cover_url)


@dataclass(slots=True)
class MediaItem:
    """Universal media item representation across categories."""
    id: str
    title: str
    category: Category
    source_id: str
    page_url: str
    original_title: str | None = None
    release_year: int | None = None
    poster_url: str | None = None
    description: str | None = None

    # Category-specific payloads
    movie_variants: list[MovieDownloadVariant] = field(default_factory=list)
    stream_url: str | None = None  # Opportunistic video/audio stream
    game_releases: list[GameRelease] = field(default_factory=list)
    music_tracks: list[MusicTrack] = field(default_factory=list)

    # Source health/kind for template branching (_music_card.html). Plain str, not
    # SourceKind: every pre-006 constructor site and the DB rehydrate path default
    # to "full" without importing the enum. Set in _collect_items from config.kind.
    source_kind: str = "full"

    def __post_init__(self):
        validate_media_url(self.page_url)
        if self.poster_url:
            validate_media_url(self.poster_url)
        if self.stream_url:
            validate_media_url(self.stream_url)


@dataclass(slots=True)
class CachedResult:
    """In-memory cache entry."""
    key: str
    items: list[MediaItem]
    created_at: float = field(default_factory=time.time)
    ttl_seconds: int = 2700  # 45 minutes

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds
