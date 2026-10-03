# Data Model: Backend API and UI Alignment & Gap Resolution

**Feature Branch**: `009-backend-api-ui-alignment`  
**Date**: 2026-10-03  
**Spec Reference**: `specs/009-backend-api-ui-alignment/spec.md`

---

## 1. Relational Database Schema (SQLite + WAL)

The persistent database lives at `apps/api/data/index.db`. All connections enforce:
```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 10000;
```

---

### Table: `media_items`
Core media catalog records across movies, series, games, and music.

```sql
CREATE TABLE IF NOT EXISTS media_items (
    id                  TEXT PRIMARY KEY,                  -- Unique slug or hash (e.g., "digger-2024", "nex1-12345")
    category            TEXT NOT NULL,                     -- 'movies' | 'games' | 'music'
    source_id           TEXT NOT NULL,                     -- Scraper plugin identifier (e.g., 'uptvs', 'yasdl')
    title               TEXT NOT NULL,                     -- Persian or English display title
    title_norm          TEXT NOT NULL,                     -- NFKC normalized, stripped diacritics & punctuation for indexing
    artist              TEXT NOT NULL DEFAULT '',          -- Music artist / developer / publisher
    page_url            TEXT NOT NULL,                     -- Upstream portal post URL
    poster_url          TEXT,                              -- Artwork / cover image URL
    release_year        INT,                               -- 4-digit release year
    description         TEXT,                              -- Synopses, release notes, system requirements
    watch_url           TEXT,                              -- Streaming landing page for subscription portals
    stream_url          TEXT,                              -- Direct streamable MP4/HLS/MP3 URL (if available)
    release_group       TEXT,                              -- FitGirl, DODI, PaHe, etc.
    archive_password    TEXT,                              -- Extraction password for compressed archives
    total_size          TEXT,                              -- Human-readable size string (e.g., "45.2 GB")
    imdb_rating         REAL,                              -- Floating rating floor (0.0 - 10.0)
    censorship_status   TEXT NOT NULL DEFAULT 'unspecified', -- 'uncensored' | 'censored' | 'mixed' | 'unspecified'
    source_access_tier  TEXT NOT NULL DEFAULT 'free',       -- 'free' | 'premium' | 'freemium'
    is_featured         INT NOT NULL DEFAULT 0,            -- 1 = Featured in home hero / trending shelf
    view_count          INT NOT NULL DEFAULT 0,            -- Incremented on search impression / click for trending ranking
    first_seen          REAL NOT NULL,                     -- Epoch timestamp of initial scrape
    last_seen           REAL NOT NULL,                     -- Epoch timestamp of latest scrape / link verification
    UNIQUE(source_id, page_url)
);

CREATE INDEX IF NOT EXISTS idx_media_category ON media_items(category);
CREATE INDEX IF NOT EXISTS idx_media_trending ON media_items(category, is_featured DESC, view_count DESC);
CREATE INDEX IF NOT EXISTS idx_media_latest ON media_items(category, last_seen DESC);
```

---

### Table: `download_variants`
Direct download file choices for movies and music items.

```sql
CREATE TABLE IF NOT EXISTS download_variants (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id             TEXT NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
    kind                TEXT NOT NULL,                     -- 'movie' | 'music'
    label               TEXT,                              -- "1080p.HQ", "720p.x265", "320 kbps"
    quality             TEXT,                              -- "4k", "1080p", "720p", "480p"
    codec               TEXT,                              -- "x264", "x265", "HEVC", "AV1"
    audio_track         TEXT,                              -- "FA-DUB", "FA-SUB", "ORIGINAL", "EN"
    size_bytes          INT,                               -- Numeric file size in bytes
    size_text           TEXT,                              -- Formatted size (e.g. "1.8 GB")
    is_censored         INT,                               -- 1 = Censored cut, 0 = Uncensored, NULL = Unknown
    is_premium          INT NOT NULL DEFAULT 0,            -- 1 = VIP / subscription required
    url                 TEXT NOT NULL,                     -- Direct upstream CDN download URL
    access              TEXT NOT NULL DEFAULT 'direct'     -- 'direct' | 'needs_login'
);

CREATE INDEX IF NOT EXISTS idx_variants_item ON download_variants(item_id);
```

---

### Table: `game_releases` & `game_parts`
Archive part sequences and release sets for games.

```sql
CREATE TABLE IF NOT EXISTS game_releases (
    id                  TEXT NOT NULL,                     -- Unique release hash or identifier
    item_id             TEXT NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
    source_name         TEXT,                              -- Upstream source branding
    release_group       TEXT,                              -- "FitGirl", "ElAmigos", "Scene"
    version             TEXT,                              -- Game build / patch version
    total_size          TEXT,                              -- Archive total size string
    archive_password    TEXT,                              -- Decryption password
    sort_order          INT NOT NULL DEFAULT 0,
    UNIQUE(item_id, id)
);

CREATE TABLE IF NOT EXISTS game_parts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id             TEXT NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
    release_id          TEXT NOT NULL,
    part_number         INT NOT NULL,                      -- 1-based sequential part index
    part_label          TEXT NOT NULL,                     -- "Part 1", "پارت ۱"
    file_size           TEXT,                              -- "2.0 GB"
    url                 TEXT NOT NULL,                     -- Direct CDN link
    access              TEXT NOT NULL DEFAULT 'direct'
);

CREATE INDEX IF NOT EXISTS idx_game_parts_release ON game_parts(item_id, release_id, part_number);
```

---

### Table: `search_fts` (Full-Text Search Virtual Table)
High-performance trigram and token-based search virtual table.

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(
    title_norm,
    artist,
    description,
    page_url,
    item_id UNINDEXED,
    tokenize='trigram'
);
```

---

### Table: `source_configs`
Persistent operational overrides for scraper portals (addresses, mirrors, toggles).

```sql
CREATE TABLE IF NOT EXISTS source_configs (
    source_id           TEXT PRIMARY KEY,                  -- Matches code ID (e.g., 'uptvs', 'nex1music')
    category            TEXT NOT NULL,                     -- 'movies' | 'games' | 'music'
    name                TEXT NOT NULL,                     -- Human branding
    base_url            TEXT NOT NULL,                     -- Active primary base URL
    mirror_url          TEXT,                              -- Active fallback mirror URL
    enabled             INT NOT NULL DEFAULT 1,            -- 1 = Enabled, 0 = Disabled
    timeout_seconds     REAL NOT NULL DEFAULT 7.0,
    updated_at          REAL NOT NULL
);
```

---

### Table: `source_suggestions`
Community submitted portal candidates for operator review queue (Spec 004).

```sql
CREATE TABLE IF NOT EXISTS source_suggestions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    url                 TEXT NOT NULL,                     -- Target homepage URL
    domain              TEXT NOT NULL UNIQUE,              -- Normalized root domain (e.g. "example.com")
    category            TEXT NOT NULL,                     -- 'movies' | 'games' | 'music'
    source_name         TEXT NOT NULL,                     -- "Example Portal"
    proposed_tier       TEXT NOT NULL DEFAULT '1',         -- '1' | '2' | '3'
    default_audio_track TEXT NOT NULL DEFAULT 'EN',        -- 'EN' | 'FA-DUB' | 'FA-SUB'
    contact             TEXT,                              -- Optional submitter email
    notes               TEXT,                              -- Submitter comments
    status              TEXT NOT NULL DEFAULT 'pending',   -- 'pending' | 'approved' | 'rejected'
    request_count       INT NOT NULL DEFAULT 1,            -- Increment on duplicate domain submission
    created_at          REAL NOT NULL,
    updated_at          REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_suggestions_status ON source_suggestions(status, category);
```

---

### Table: `conversion_jobs`
YouTube to MP3 asynchronous task lifecycle tracking.

```sql
CREATE TABLE IF NOT EXISTS conversion_jobs (
    id                  TEXT PRIMARY KEY,                  -- UUID string
    client_ip           TEXT NOT NULL,                     -- Client IP for rate-limiting
    youtube_url         TEXT NOT NULL,                     -- Input URL
    video_id            TEXT NOT NULL,                     -- Extracted 11-char YouTube ID
    video_title         TEXT,                              -- Extracted title
    bitrate             INT NOT NULL DEFAULT 320,          -- 128 | 192 | 256 | 320
    sample_rate         INT NOT NULL DEFAULT 44100,        -- 44100 | 48000
    write_meta          INT NOT NULL DEFAULT 1,            -- 1 = Embed ID3 tags
    status              TEXT NOT NULL DEFAULT 'queued',    -- 'queued' | 'processing' | 'completed' | 'failed'
    progress            INT NOT NULL DEFAULT 0,            -- 0 to 100 percentage
    current_step        TEXT,                              -- Step description
    error_message       TEXT,                              -- Error details on failure
    created_at          REAL NOT NULL,
    completed_at        REAL
);

CREATE INDEX IF NOT EXISTS idx_conversion_client ON conversion_jobs(client_ip, created_at);
```

---

### Table: `extraction_dead_letter`
Dead-letter queue for failed or unparseable LangChain extraction attempts (User Story 7).

```sql
CREATE TABLE IF NOT EXISTS extraction_dead_letter (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id           TEXT NOT NULL,                     -- Scraper / portal source identifier
    page_url            TEXT NOT NULL,                     -- Upstream posting URL
    category            TEXT NOT NULL,                     -- 'movies' | 'games' | 'music'
    raw_html            TEXT NOT NULL,                     -- Raw HTML payload preserved for re-extraction
    error_message       TEXT NOT NULL,                     -- Diagnostic exception / timeout details
    model_name          TEXT,                              -- LLM model used during failure
    status              TEXT NOT NULL DEFAULT 'pending',   -- 'pending' | 'resolved' | 'failed'
    retry_count         INT NOT NULL DEFAULT 0,            -- Number of re-extraction attempts
    next_retry_at       REAL NOT NULL,                     -- Scheduled epoch timestamp for next retry
    created_at          REAL NOT NULL,                     -- Timestamp of initial failure
    resolved_at         REAL                               -- Timestamp of successful re-extraction
);

CREATE INDEX IF NOT EXISTS idx_dlq_status ON extraction_dead_letter(status, next_retry_at);
```

---

### Table: `domain_throttle_state`
Per-domain adaptive rate limiting and backoff state (User Story 6).

```sql
CREATE TABLE IF NOT EXISTS domain_throttle_state (
    domain              TEXT PRIMARY KEY,                  -- Normalized root domain (e.g. "doostihaa.com")
    consecutive_429     INT NOT NULL DEFAULT 0,            -- Count of consecutive rate-limit signals
    current_delay_sec   REAL NOT NULL DEFAULT 1.0,         -- Dynamic delay between requests
    backoff_until       REAL NOT NULL DEFAULT 0,           -- Epoch timestamp until domain is unblocked
    total_requests      INT NOT NULL DEFAULT 0,            -- Aggregate request counter
    total_throttled     INT NOT NULL DEFAULT 0,            -- Aggregate 429/timeout counter
    updated_at          REAL NOT NULL
);
```

---

### Table: `operator_users`
Administrator credentials for source configuration edits and queue triage.

```sql
CREATE TABLE IF NOT EXISTS operator_users (
    username            TEXT PRIMARY KEY,
    password_hash       TEXT NOT NULL,                     -- Argon2 or bcrypt hash
    role                TEXT NOT NULL DEFAULT 'operator',  -- 'operator' | 'admin'
    created_at          REAL NOT NULL
);
```

---

## 2. LangChain Pydantic Extraction Schemas

These models govern structured extraction from unstructured portal HTML:

```python
from pydantic import BaseModel, Field

class ExtractedDownloadVariant(BaseModel):
    quality: str = Field(description="Resolution e.g. 1080p, 720p, 480p, 4K")
    codec: str = Field(default="x264", description="Codec e.g. x264, x265, HEVC")
    audio_track: str = Field(default="ORIGINAL", description="FA-DUB, FA-SUB, or ORIGINAL")
    file_size_text: str = Field(default="", description="Human readable size e.g. 1.8 GB")
    download_url: str = Field(description="Direct HTTP/HTTPS link to media file")
    is_censored: bool | None = Field(default=None, description="Whether this cut is censored")
    is_premium: bool = Field(default=False, description="Whether VIP login is required")

class MovieExtractionResult(BaseModel):
    title: str = Field(description="Movie or series title")
    release_year: int | None = Field(default=None, description="Release year")
    description: str = Field(default="", description="Plot synopsis or description")
    poster_url: str | None = Field(default=None, description="Image cover URL")
    imdb_rating: float | None = Field(default=None, description="IMDb score 0.0-10.0")
    variants: list[ExtractedDownloadVariant] = Field(default_factory=list)

class ExtractedGamePart(BaseModel):
    part_number: int = Field(description="1-based integer sequence number")
    part_label: str = Field(description="Label e.g. Part 1, پارت ۱")
    file_size: str = Field(default="", description="Size e.g. 2 GB")
    download_url: str = Field(description="Direct download URL for part archive")

class GameReleaseExtractionResult(BaseModel):
    title: str = Field(description="Game title")
    release_group: str = Field(default="", description="FitGirl, DODI, etc.")
    version: str = Field(default="", description="Patch / build version")
    total_size: str = Field(default="", description="Total unpacked size")
    archive_password: str = Field(default="", description="Archive extraction password")
    parts: list[ExtractedGamePart] = Field(default_factory=list)

class MusicTrackExtractionResult(BaseModel):
    title: str = Field(description="Track or album title")
    artist: str = Field(default="", description="Artist or band name")
    poster_url: str | None = Field(default=None, description="Album artwork URL")
    stream_url: str | None = Field(default=None, description="Online preview audio URL")
    downloads: list[ExtractedDownloadVariant] = Field(default_factory=list)
```
