# Data Model: Source Tier Filtering, Censorship Metadata, and IMDb Ratings

**Branch**: `007-source-filters-movie-details` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

This document defines the domain models, data types, validation rules, and schema extensions for the feature.

---

## Enums

### 1. `SourceAccessTier`
Represents the business and access model of an upstream media source.

| Value | Persian Label | Description |
|-------|---------------|-------------|
| `free` | رایگان | All download links are freely accessible without registration or paid subscription. |
| `premium` | اشتراکی / VIP | All download links require a paid VIP membership or subscription account. |
| `freemium` | ترکیبی | Basic qualities are free; high definition/bitrate links require VIP membership. |

### 2. `CensorshipStatus`
Represents the censorship classification of a movie title or media item.

| Value | Persian Label | Badge Theme Token | Description |
|-------|---------------|-------------------|-------------|
| `uncensored` | نسخه کامل / بدون سانسور | Emerald (`bg-emerald-500/20 text-emerald-300 border-emerald-500/40`) | Verified untouched, complete release. |
| `censored` | بازبینی شده / سانسور شده | Amber (`bg-amber-500/20 text-amber-300 border-amber-500/40`) | Verified edited or censored for broadcast/compliance. |
| `mixed` | شامل هر دو نسخه | Cyan (`bg-cyan-500/20 text-cyan-300 border-cyan-500/40`) | Contains both censored and uncensored download variants. |
| `unspecified` | نامشخص | Zinc (`bg-zinc-800/60 text-zinc-400 border-zinc-700/60`) | Censorship status not declared in upstream metadata. |

---

## Domain Entity Extensions

### `SourceConfig` (Backend `apps/api/models.py`)

Configuration metadata for a registered scraper source.

```python
@dataclass(slots=True)
class SourceConfig:
    id: str
    name: str
    category: Category
    base_urls: list[str] = field(default_factory=list)
    enabled: bool = True
    timeout_seconds: float = 7.0
    access_tier: SourceAccessTier = SourceAccessTier.FREE
```

### `MovieDownloadVariant` (Backend & Frontend)

Individual downloadable file variant under a movie title.

**Python (`apps/api/models.py`)**:
```python
@dataclass(slots=True)
class MovieDownloadVariant:
    id: str
    quality: str
    codec: str
    audio_track: str
    download_url: str
    file_size_mb: float | None = None
    source_name: str = ""
    is_censored: bool | None = None
    is_premium: bool = False
```

**TypeScript (`apps/web/src/types/media.ts`)**:
```typescript
export interface MovieDownloadVariant {
  id: string
  quality: string
  codec: string
  audio_track: string
  download_url: string
  file_size_mb: number | null
  source_name: string
  is_censored?: boolean | null
  is_premium?: boolean
}
```

### `MediaItem` (Backend & Frontend)

Aggregated media item presented in search results and card grids.

**Python (`apps/api/models.py`)**:
```python
@dataclass(slots=True)
class MediaItem:
    id: str
    title: str
    category: Category
    source_id: str
    page_url: str
    original_title: str | None = None
    release_year: int | None = None
    poster_url: str | None = None
    description: str | None = None
    stream_url: str | None = None

    # New metadata fields
    imdb_rating: float | None = None
    censorship_status: CensorshipStatus = CensorshipStatus.UNSPECIFIED
    source_access_tier: SourceAccessTier = SourceAccessTier.FREE

    # Category-specific payloads
    movie_variants: list[MovieDownloadVariant] = field(default_factory=list)
    game_releases: list[GameRelease] = field(default_factory=list)
    music_tracks: list[MusicTrack] = field(default_factory=list)
```

**TypeScript (`apps/web/src/types/media.ts`)**:
```typescript
export type SourceAccessTier = 'free' | 'premium' | 'freemium'
export type CensorshipStatus = 'uncensored' | 'censored' | 'mixed' | 'unspecified'

export interface MediaItem {
  id: string
  title: string
  category: Category
  source_id: string
  page_url: string
  original_title: string | null
  release_year: number | null
  poster_url: string | null
  description: string | null
  stream_url: string | null

  // New metadata fields
  imdb_rating: number | null
  censorship_status: CensorshipStatus
  source_access_tier: SourceAccessTier

  movie_variants: MovieDownloadVariant[]
  game_releases: GameRelease[]
  music_tracks: MusicTrack[]
}
```

### `SourceStatus` (Backend API Response & Frontend)

Status object returned by `GET /api/sources/status`.

```typescript
export interface SourceStatus {
  id: string
  name: string
  category: string
  base_url: string
  enabled: boolean
  access_tier: SourceAccessTier
}
```

---

## Client Filter State Model

**TypeScript (`apps/web/src/components/InViewFilterBar.tsx`)**:
```typescript
export interface FilterState {
  qualities: string[]
  audioTracks: string[]
  sources: string[]
  accessTier: 'all' | 'free' | 'premium'
  censorship: 'all' | 'uncensored' | 'censored'
}
```

### Filter Evaluation Matrix

| Selected Filter | Item Inclusion Rule | Variant Refinement Rule |
|-----------------|---------------------|--------------------------|
| `accessTier: 'all'` | Include all items | Show all variants |
| `accessTier: 'free'` | Include `source_access_tier == 'free'` OR (`'freemium'` with free variants) | For freemium items, display only variants where `is_premium == false` |
| `accessTier: 'premium'` | Include `source_access_tier == 'premium'` OR (`'freemium'` with VIP variants) | For freemium items, display only variants where `is_premium == true` |
| `censorship: 'all'` | Include all items | Show all variants |
| `censorship: 'uncensored'` | Include `censorship_status == 'uncensored'` OR (`'mixed'` with uncensored variants) | For mixed items, display only variants where `is_censored == false` |
| `censorship: 'censored'` | Include `censorship_status == 'censored'` OR (`'mixed'` with censored variants) | For mixed items, display only variants where `is_censored == true` |

---

## Validation Rules

1. **`imdb_rating`**:
   - Must be a float between `0.0` and `10.0` inclusive, rounded to 1 decimal place.
   - Any string parsed as NaN or out of range must resolve to `None`.
2. **`censorship_status` derivation**:
   - If variants have mixed flags (`is_censored=True` and `is_censored=False`), status MUST be `CensorshipStatus.MIXED`.
   - If all variants are `is_censored=True` (or title/tags state censored), status MUST be `CensorshipStatus.CENSORED`.
   - If all variants are `is_censored=False` (or title/tags state uncensored/نسخه کامل), status MUST be `CensorshipStatus.UNCENSORED`.
   - Otherwise, status MUST be `CensorshipStatus.UNSPECIFIED`.
