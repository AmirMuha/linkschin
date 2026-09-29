# Data Model: Modern Web Interface and UI/UX Redesign

- **Feature**: `002-ui-ux-redesign`
- **Date**: 2026-09-29
- **Status**: Complete

This document defines the data entities, schema contracts, UI state models, and validation invariants governing the modern web interface (`apps/web`) and its interaction with the backend aggregator (`apps/api`).

---

## Entity Relationship Overview

```text
Backend REST API (FastAPI)                         Frontend Web Client (Next.js)
┌───────────────────────────────────────┐          ┌───────────────────────────────────────┐
│ SearchQuery                           │          │ SearchState                           │
│  - raw_query: string                  │  JSON    │  - query: string                      │
│  - normalized_query: string           │ ───────> │  - category: Category                 │
│  - category: Category                 │ Response │  - items: MediaItem[]                 │
│                                       │          │  - warnings: string[]                 │
│ SearchApiResponse                     │          │  - is_cached: boolean                 │
│  - items: MediaItem[]                 │          │  - is_loading: boolean                │
│  - warnings: string[]                 │          └───────────────────────────────────────┘
│  - is_cached: boolean                 │                              │
│  - query: string                      │                              ▼
│  - category: string                   │          ┌───────────────────────────────────────┐
└───────────────────────────────────────┘          │ InViewFilterState                     │
                   │                               │  - selected_qualities: Set<string>    │
                   ▼                               │  - selected_audio: Set<string>        │
┌───────────────────────────────────────┐          │  - selected_sources: Set<string>      │
│ MediaItem                             │          └───────────────────────────────────────┘
│  - id: string                         │                              │
│  - title: string                      │                              ▼
│  - original_title: string | null      │          ┌───────────────────────────────────────┐
│  - category: Category                 │          │ ActivePlayerState                     │
│  - release_year: number | null        │          │  - current_track: MusicTrack | null   │
│  - poster_url: string | null          │          │  - is_playing: boolean                │
│  - description: string | null         │          │  - current_time: number               │
│  - source_id: string                  │          │  - duration: number                   │
│  - page_url: string                   │          │  - volume: number (0.0 - 1.0)         │
│  - stream_url: string | null          │          └───────────────────────────────────────┘
│                                       │
│  [Category Specific Payloads]         │
│  - movie_variants: MovieVariant[]     │
│  - game_releases: GameRelease[]       │
│  - music_tracks: MusicTrack[]         │
└───────────────────────────────────────┘
```

---

## 1. Domain Entities (Server & Client Shared)

### `Category` (Enum)
Media categorization domain:
- `"movies"`: Movies and TV series.
- `"games"`: PC and console game repack archives and releases.
- `"music"`: Songs, singles, albums, and tracks.

### `MovieDownloadVariant`
A distinct video download option belonging to a movie/series item:
- `id` (string): Unique identifier (e.g. `"film2media-1080p-x265-dubbed"`).
- `quality` (string): Standardized resolution tag (`"4K"`, `"1080p"`, `"720p"`, `"480p"`).
- `codec` (string): Video encoding standard (`"x264"`, `"x265"`, `"10bit"`, `"HEVC"`, `"BluRay"`, `"WEB-DL"`).
- `audio_track` (string): Audio specification (`"Persian Dubbed"`, `"Soft Subtitled"`, `"Original Audio"`).
- `file_size_mb` (number | null): File size in megabytes.
- `download_url` (string): Direct upstream CDN download URL.
- `source_name` (string): Upstream portal display name (e.g. `"UpTVs"`, `"Doostihaa"`).

### `GamePartLink`
An individual file part of a split multi-part game archive:
- `part_number` (integer): Sequential part number (1-indexed: 1, 2, 3... N).
- `part_label` (string): Display label (e.g. `"Part 1"`, `"پارت ۱"`).
- `file_size` (string | null): Formatted part size (e.g. `"2.0 GB"`, `"950 MB"`).
- `download_url` (string): Direct upstream CDN download URL.

### `GameRelease`
A complete game repack or scene release package:
- `id` (string): Unique release package ID.
- `source_name` (string): Upstream source name (e.g. `"YasDL"`).
- `release_group` (string): Repack group or scene team (e.g. `"FitGirl"`, `"DODI"`, `"ElAmigos"`, `"CODEX"`).
- `version` (string): Game version, build number, or patch tag (e.g. `"v1.0.4 + All DLCs"`).
- `total_size` (string): Total download size string (e.g. `"42.8 GB"`).
- `archive_password` (string): Extraction password (e.g. `"www.yasdl.com"`).
- `parts` (GamePartLink[]): Ordered array of archive parts.
- `has_missing_parts` (boolean): Flag indicating non-consecutive or missing parts.
- `missing_part_numbers` (number[]): Array of missing part numbers if any gap exists.

### `MusicDownloadVariant`
Audio quality download link:
- `bitrate` (string): Bitrate specifier (`"320kbps"`, `"128kbps"`).
- `download_url` (string): Direct MP3 download URL.
- `file_size` (string | null): Formatted file size string (e.g. `"8.5 MB"`).

### `MusicTrack`
A discovered music track or single:
- `id` (string): Unique track ID.
- `title` (string): Song title in Persian or English.
- `artist` (string): Artist name.
- `album` (string | null): Album title if available.
- `cover_url` (string | null): Direct image URL for album/track artwork.
- `stream_url` (string | null): Direct MP3 stream URL for in-browser playback.
- `downloads` (MusicDownloadVariant[]): Array of available bitrate download variants.
- `source_name` (string): Upstream portal name (e.g. `"Nex1Music"`).

### `MediaItem`
Universal media representation returned by search:
- `id` (string): Deterministic unique ID (e.g. `"movies-inception-2010-uptvs"`).
- `title` (string): Display title (Persian or localized).
- `original_title` (string | null): Original international title.
- `category` (Category): Active category.
- `source_id` (string): Scraper source ID (e.g. `"uptvs"`, `"doostihaa"`, `"yasdl"`, `"nex1music"`).
- `page_url` (string): Source website article URL.
- `release_year` (number | null): 4-digit release year.
- `poster_url` (string | null): Cover image URL.
- `description` (string | null): Synopsis or summary.
- `stream_url` (string | null): Direct video or audio stream URL if verified.
- `movie_variants` (MovieDownloadVariant[]): Populated for `movies`.
- `game_releases` (GameRelease[]): Populated for `games`.
- `music_tracks` (MusicTrack[]): Populated for `music`.

### `SearchApiResponse`
Standardized payload returned by `GET /api/search`:
- `query` (string): Raw search query.
- `category` (string): Queried category.
- `is_cached` (boolean): Whether results originated from cache/database.
- `items` (MediaItem[]): Discovered media items.
- `warnings` (string[]): Non-blocking alerts (e.g. source timeouts or degraded scrapers).

### `SourceStatus`
Payload returned by `GET /api/sources`:
- `id` (string): Source identifier.
- `name` (string): Display name.
- `category` (string): Media category.
- `base_url` (string): Primary base URL.
- `enabled` (boolean): Operational status.

---

## 2. Client-Side UI State Models (`apps/web`)

### `SearchUIState`
Active search query and response state:
- `query`: Current input query string.
- `category`: Active `Category` tab (`"movies"`, `"games"`, `"music"`).
- `isLoading`: Boolean indicating in-flight network request.
- `items`: Array of `MediaItem` matching current query.
- `warnings`: Array of warning messages from responding sources.
- `isCached`: Boolean indicating whether current result set was cached.
- `error`: Error message if network request fails entirely.

### `InViewFilterState`
Local filter criteria applied in-memory over loaded `MediaItem[]`:
- `selectedQualities`: Set of quality tags (e.g. `{"1080p", "4K"}`).
- `selectedAudio`: Set of audio types (e.g. `{"Persian Dubbed"}`).
- `selectedSources`: Set of source IDs (e.g. `{"uptvs", "yasdl"}`).
- `minYear`: Optional lower bound on release year.
- `maxYear`: Optional upper bound on release year.

### `ActivePlayerState`
Singleton state for the global audio preview player:
- `track`: Currently playing `MusicTrack | null`.
- `isPlaying`: Boolean play/pause state.
- `currentTime`: Current playback position in seconds.
- `duration`: Track total duration in seconds.
- `volume`: Floating-point volume level (`0.0` to `1.0`), persisted in `localStorage`.
- `isMuted`: Boolean mute toggle state.

### `ClipboardToastState`
Transient UI feedback for clipboard operations:
- `visible`: Boolean flag.
- `message`: Toast text (e.g. `"رمز کپی شد"`, `"تمام لینک‌ها کپی شدند"`).
- `type`: `"success"` | `"error"` | `"fallback"`.
- `timeoutId`: Timer handle for auto-dismissal (typically 2500ms).

---

## 3. Invariants & Validation Rules

1. **Direct CDN Invariant (Constitution Principle III)**:
   - Every `download_url` and `stream_url` must point directly to an external HTTP/HTTPS host.
   - The application server and Next.js backend never serve media payloads; no internal proxy routes (`/api/proxy/media/*`) are permitted.

2. **Bidirectional Typography Isolation**:
   - All Persian titles, synopses, and notes must be rendered within RTL containers (`dir="rtl"`).
   - All technical filenames, release groups, codecs (e.g. `x265`, `1080p`), archive part numbers, passwords, hashes, and URLs must be isolated with `dir="ltr"` and `unicode-bidi: isolate` / `font-mono` to prevent punctuation reversal defects in RTL mode.

3. **Game Archive Sequential Integrity**:
   - `GameRelease.parts` must be sorted ascending by `part_number`.
   - If any `part_number` in `1..N` is missing, `has_missing_parts` must be `true`, and missing numbers recorded in `missing_part_numbers` to trigger a UI warning.

4. **Single-Instance Audio Playback**:
   - At most one audio stream may be active at any given moment. Starting playback of any track immediately terminates the prior track's stream.

5. **Download Manager Compatibility**:
   - Batch export ("Copy All Links") must format links strictly as newline-delimited URLs (`\n`), cleanly consumable by clipboard-monitoring download managers.
