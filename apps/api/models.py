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
class SourceAccessTier(str, Enum):
    """Upstream source access model."""
    FREE = "free"
    PREMIUM = "premium"
    FREEMIUM = "freemium"

class CensorshipStatus(str, Enum):
    """Censorship classification of a movie release."""
    UNCENSORED = "uncensored"
    CENSORED = "censored"
    MIXED = "mixed"
    UNSPECIFIED = "unspecified"


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
    access_tier: SourceAccessTier = SourceAccessTier.FREE
    # FR-003: a subscription/regional-availability service returns a watch destination
    # instead of a public download. Default True keeps every existing source unchanged.
    provides_downloads: bool = True
    # Indicates whether the source is a streaming platform (like Filimo, Aparat, etc.)
    is_streaming: bool = False
    # FR-021: when set, this id is an alias of another source and must not open a
    # second result stream for the same site.
    duplicate_of: str | None = None

    @property
    def is_alias(self) -> bool:
        return bool(self.duplicate_of)

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
    # "direct" (default) or "needs_login" when the host answers with an
    # interstitial page instead of the file.
    access: str = "direct"
    is_censored: bool | None = None
    is_premium: bool = False

    def __post_init__(self):
        validate_media_url(self.download_url)


@dataclass(slots=True)
class GamePartLink:
    """Individual archive part link for multi-part game downloads."""
    part_number: int
    part_label: str
    download_url: str
    file_size: str | None = None
    access: str = "direct"

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
    access: str = "direct"

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

    # Enrichment metadata (spec 007)
    imdb_rating: float | None = None
    censorship_status: CensorshipStatus = CensorshipStatus.UNSPECIFIED
    source_access_tier: SourceAccessTier = SourceAccessTier.FREE

    # Category-specific payloads
    movie_variants: list[MovieDownloadVariant] = field(default_factory=list)
    # FR-006: a page on the SOURCE'S OWN site where the title may legitimately be
    # watched. Deliberately NOT `stream_url`, which is a playable direct-file URL --
    # a watch destination is a page a human opens, never a media payload we touch.
    watch_url: str | None = None
    stream_url: str | None = None  # Opportunistic video/audio stream
    game_releases: list[GameRelease] = field(default_factory=list)
    music_tracks: list[MusicTrack] = field(default_factory=list)

    # Source health/kind for client-side branching. Plain str, not
    # SourceKind: every pre-006 constructor site and the DB rehydrate path default
    # to "full" without importing the enum. Set in _collect_items from config.kind.
    source_kind: str = "full"
    is_featured: bool = False
    view_count: int = 0

    def __post_init__(self):
        validate_media_url(self.page_url)
        if self.poster_url:
            validate_media_url(self.poster_url)
        if self.watch_url:
            validate_media_url(self.watch_url)
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


# ============================================================================
# Pydantic Schemas for AI Extraction & API Request/Response Payloads
# ============================================================================

from pydantic import BaseModel, Field  # noqa: E402


class ExtractedDownloadVariant(BaseModel):
    quality: str = Field(default="1080p", description="Resolution e.g. 1080p, 720p, 480p, 4k")
    codec: str = Field(default="x264", description="Codec e.g. x264, x265, HEVC")
    audio_track: str = Field(default="ORIGINAL", description="FA-DUB, FA-SUB, or ORIGINAL")
    file_size_text: str = Field(default="", description="Human readable size e.g. 1.8 GB")
    download_url: str = Field(default="", description="Direct HTTP/HTTPS link to media file")
    is_censored: bool | None = Field(default=None, description="Whether this cut is censored")
    is_premium: bool = Field(default=False, description="Whether VIP login is required")


class MovieExtractionResult(BaseModel):
    title: str = Field(default="", description="Movie or series title")
    release_year: int | None = Field(default=None, description="Release year")
    description: str = Field(default="", description="Plot synopsis or description")
    poster_url: str | None = Field(default=None, description="Image cover URL")
    imdb_rating: float | None = Field(default=None, description="IMDb score 0.0-10.0")
    variants: list[ExtractedDownloadVariant] = Field(default_factory=list)


class ExtractedGamePart(BaseModel):
    part_number: int = Field(default=1, description="1-based integer sequence number")
    part_label: str = Field(default="Part 1", description="Label e.g. Part 1, پارت ۱")
    file_size: str = Field(default="", description="Size e.g. 2 GB")
    download_url: str = Field(default="", description="Direct download URL for part archive")


class GameReleaseExtractionResult(BaseModel):
    title: str = Field(default="", description="Game title")
    release_group: str = Field(default="", description="FitGirl, DODI, etc.")
    version: str = Field(default="", description="Patch / build version")
    total_size: str = Field(default="", description="Total unpacked size")
    archive_password: str = Field(default="", description="Archive extraction password")
    parts: list[ExtractedGamePart] = Field(default_factory=list)


class MusicTrackExtractionResult(BaseModel):
    title: str = Field(default="", description="Track or album title")
    artist: str = Field(default="", description="Artist or band name")
    poster_url: str | None = Field(default=None, description="Album artwork URL")
    stream_url: str | None = Field(default=None, description="Online preview audio URL")
    downloads: list[ExtractedDownloadVariant] = Field(default_factory=list)


# --- API Request Payloads ---

class SuggestionCreateRequest(BaseModel):
    url: str
    category: str
    source_name: str
    proposed_tier: str = "1"
    default_audio_track: str = "EN"
    contact: str | None = None
    notes: str | None = None


class SourceUpdateRequest(BaseModel):
    base_url: str | None = None
    mirror_url: str | None = None


class SourceToggleRequest(BaseModel):
    enabled: bool


class ConvertCreateRequest(BaseModel):
    url: str
    bitrate: int = 320
    sample_rate: int = 44100
    write_meta: bool = True
    norm_filename: bool = False


class ChatMessageRequest(BaseModel):
    message: str
    session_id: str | None = None
    category: str = "movies"


class LoginRequest(BaseModel):
    username: str
    password: str

