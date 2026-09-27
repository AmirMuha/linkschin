# Data Model: Iranian Multi-Media Direct Link Aggregator (MVP)

- **Feature**: `001-mvp`
- **Date**: 2026-09-27
- **Status**: Complete

This document details the core data entities, attributes, relationships, and validation rules for the multi-media aggregator.

---

## Entity Diagram

```text
Category (enum)
   │
   ├── Movies ──> MediaItem ──< MovieDownloadVariant (quality, codec, audio, direct_url)
   │                       └── StreamOffer (optional in-browser stream)
   │
   ├── Games  ──> MediaItem ──< GameRelease (release_group, password, total_size)
   │                                  └──< GamePartLink (part_num, size, direct_url)
   │
   └── Music  ──> MediaItem ──< MusicTrack (artist, album, stream_url)
                                      └──< MusicDownloadVariant (bitrate, direct_url)
```

---

## Entities & Schemas

### 1. `Category` (Enum)
Represents the active domain for search and scraping.
- `movies`: Movies and TV series.
- `games`: PC and console game repacks, setups, and updates.
- `music`: Persian singles, albums, and tracks.

---

### 2. `SourceConfig`
Configuration for an upstream Iranian website scraper.
- `id` (string, unique): E.g., `"film2media"`, `"yasdl"`, `"nex1music"`.
- `name` (string): Human-readable title, e.g. `"Film2Media"`.
- `category` (`Category`): The category this source serves.
- `base_urls` (list of strings): Primary URL and fallback/mirror URLs.
- `enabled` (boolean): Toggle for enabling/disabling the scraper without code deletion.
- `timeout_seconds` (float, default: `7.0`): Max wait time for this specific scraper.

---

### 3. `SearchQuery`
User search parameters and normalized metadata.
- `raw_query` (string): User input (e.g. `"Inception 2010"`, `"تلقین"`, `"GTA V"`).
- `normalized_query` (string): Cleaned string with Persian character normalization (`ي` → `ی`, `ك` → `ک`), stripped punctuation, and extracted year.
- `category` (`Category`): Active tab category.
- `extracted_year` (optional integer): Parsed 4-digit release year if detected.

---

### 4. `MediaItem`
High-level media entity discovered across one or more portals.
- `id` (string): Deterministic hash or slug based on `(category, normalized_title, year)`.
- `title` (string): Display title in Persian or English.
- `original_title` (optional string): International / English title.
- `category` (`Category`): Media type.
- `release_year` (optional integer): E.g. `2024`.
- `poster_url` (optional string): Cover image URL.
- `description` (optional string): Short plot or summary snippet.
- `source_id` (string): Upstream source portal identifier.
- `page_url` (string): Link to the original post on the source website.

---

### 5. `MovieDownloadVariant`
A specific video download file associated with a movie/series.
- `id` (string): Unique variant identifier.
- `quality` (string): E.g. `"1080p"`, `"720p"`, `"480p"`, `"4K"`.
- `codec` (string): E.g. `"x264"`, `"x265"`, `"10bit"`, `"Web-DL"`, `"BluRay"`.
- `audio_track` (string): `"Persian Dubbed"`, `"Persian Soft-Sub"`, or `"Original Audio"`.
- `file_size_mb` (optional float): File size in megabytes.
- `download_url` (string): Direct HTTP/HTTPS download link.
- `source_name` (string): E.g. `"Film2Media"`.

---

### 6. `GameRelease`
A game package release (e.g. repack or full scene release).
- `id` (string): Unique release identifier.
- `release_group` (optional string): E.g. `"FitGirl Repack"`, `"DODI"`, `"ElAmigos"`, `"CODEX"`.
- `version` (optional string): Game version or update patch tag.
- `total_size` (string): E.g. `"45.2 GB"`.
- `archive_password` (optional string): Extraction password (e.g. `"www.yasdl.com"`).
- `parts` (list of `GamePartLink`): Ordered array of archive segment links.
- `source_name` (string): E.g. `"YasDL"`.

---

### 7. `GamePartLink`
An individual segment of a split game archive.
- `part_number` (integer): Sequential part number (`1`, `2`, `3`...).
- `part_label` (string): E.g. `"Part 1"`, `"پارت 1"`.
- `file_size` (optional string): E.g. `"2.0 GB"`.
- `download_url` (string): Direct file download URL.

---

### 8. `MusicTrack`
A discovered music single or album track.
- `id` (string): Unique track identifier.
- `title` (string): Song title.
- `artist` (string): Artist name.
- `album` (optional string): Album title.
- `cover_url` (optional string): Cover artwork URL.
- `stream_url` (optional string): Direct MP3 URL used for inline audio playback.
- `downloads` (list of `MusicDownloadVariant`): Available download options.
- `source_name` (string): E.g. `"Nex1Music"`.

---

### 9. `MusicDownloadVariant`
Specific audio bitrate download link.
- `bitrate` (string): E.g. `"320kbps"`, `"128kbps"`.
- `file_size` (optional string): E.g. `"9.4 MB"`.
- `download_url` (string): Direct MP3 file URL.

---

### 10. `CachedResult`
In-memory cache entry for search queries.
- `key` (string): `"{category}:{normalized_query}"`.
- `items` (list of `MediaItem`): Aggregated results with attached download variants.
- `created_at` (float): Unix epoch timestamp.
- `ttl_seconds` (integer, default `2700` = 45 min): Cache lifetime.
- `is_expired` (property): Computed boolean indicating if current time exceeds `created_at + ttl_seconds`.

---

## Validation Rules & Invariants

1. **Part Numbering Continuity**: In `GameRelease`, `parts` MUST be sorted strictly ascending by `part_number`. If a gap is detected (`part_number` sequence is non-consecutive), the release object marks `has_missing_parts = True` and records the missing indices.
2. **URL Scheme Enforcement**: All `download_url` and `stream_url` values MUST use `http://` or `https://` schemes. Javascript, data, or file URIs are strictly rejected.
3. **Persian Text Normalization**: All search queries and matching keys apply Unicode normalization (Form NFKC) and swap Arabic variants:
   - `ي` (Arabic Yeh) → `ی` (Persian Yeh)
   - `ك` (Arabic Kaf) → `ک` (Persian Keheh)
4. **No Server-Side Media Retention**: Entities store metadata and direct URLs only. No fields for stored binary media content or local file paths exist.
