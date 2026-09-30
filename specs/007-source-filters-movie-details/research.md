# Technical Research: Source Tier Filtering, Censorship Metadata, and IMDb Ratings

**Branch**: `007-source-filters-movie-details` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

## Summary of Decisions

This document details the architectural choices and patterns for implementing website tier filtering (Free vs. Premium), censorship metadata extraction and filtering, and IMDb rating badge presentation.

---

### Decision 1: Source Access Tier Modeling

**Context**: Upstream sources in Iran operate under three distinct business models:
1. **100% Free**: Sites like UpTVs that provide all direct download links without requiring user registration or payment.
2. **100% Premium / VIP**: Sites that lock all download links behind paid subscriptions.
3. **Freemium**: Sites that provide standard definition (480p, 720p) links freely, but require VIP subscriptions for 1080p, 4K, or high-bitrate releases.

**Decision**:
- Add `access_tier: SourceAccessTier` enum (`free`, `premium`, `freemium`) to `SourceConfig` in `apps/api/models.py` and register each source's default tier in `DEFAULT_CONFIGS` in `apps/api/sources/__init__.py`.
- Include `source_access_tier` on the aggregated `MediaItem` domain model so client applications know the access model of the source without extra lookups.
- On `MovieDownloadVariant`, add an `is_premium: bool = False` flag to differentiate free vs. VIP links on freemium sites.
- When the user selects `Free Sources Only`, freemium items remain visible in the search results, but their download matrix filters out variants marked `is_premium=True`.

**Rationale**:
- Avoids blanket-excluding freemium sources when a user wants free downloads, maximizing available titles while preventing dead-end clicks on paid links.
- Respects YAGNI: Source access tier is statically declared in source configuration rather than dynamically probed on each search.

**Alternatives Considered**:
- *Dynamic per-link subscription probing*: Over-engineered, increases upstream scraper latency, and risks account bans.
- *Strict binary Free vs. Premium flag*: Fails to model hybrid freemium websites accurately.

---

### Decision 2: Censorship Metadata Extraction & Filtering Strategy

**Context**: Iranian media consumers strongly prioritize knowing whether a movie is censored ("بازبینی شده" / "سانسور شده") or uncut ("بدون سانسور" / "نسخه کامل"). Some sources specialize exclusively in censored or uncensored content, while others offer both versions for the same movie.

**Decision**:
- Define `CensorshipStatus` enum in backend (`apps/api/models.py`) and frontend (`apps/web/src/types/media.ts`):
  - `uncensored`: Verified uncut release.
  - `censored`: Verified edited/censored release.
  - `mixed`: Contains both censored and uncensored download variants.
  - `unspecified`: Censorship status cannot be reliably determined from source metadata.
- Scraper parsing:
  - Check page title, tags, and badge keywords using normalized Persian regexes (`سانسور شده`, `بازبینی شده`, `نسخه کامل`, `بدون سانسور`).
  - At the variant level, inspect download link anchor text and URLs for variant-specific censorship flags (`is_censored: bool | None`).
  - If a media item contains both `is_censored=True` and `is_censored=False` variants, the parent item status resolves to `mixed`.
  - If no indicator is present, status is `unspecified`.
- Filtering Rule:
  - `All`: Shows all items.
  - `Uncensored Only`: Shows items where `censorship_status == 'uncensored'` or `mixed` (filtering variant list to uncensored only). Excludes `censored` and `unspecified` to preserve strict verification.
  - `Censored Only`: Shows items where `censorship_status == 'censored'` or `mixed` (filtering variant list to censored only). Excludes `uncensored` and `unspecified`.

**Rationale**:
- Guarantees strict user trust: Users requesting "Uncensored Only" are never served unverified releases.
- Accurately models sources that bundle both cuts under a single post.

**Alternatives Considered**:
- *Heuristic assumption that unspecified equals uncensored*: Unsafe; causes user dissatisfaction when a family inadvertently downloads unedited material or vice-versa.
- *Discarding unspecified items entirely from search*: Decreases overall result recall when sources simply omit the label.

---

### Decision 3: IMDb Score Extraction & Fallback Strategy

**Context**: Users want to see IMDb ratings on each movie card. Upstream sites usually scrape or embed IMDb scores in their article HTML, but some domestic or niche films lack ratings.

**Decision**:
- Add `imdb_rating: float | None = None` to `MediaItem`.
- Extract numeric scores in scraper plugins from:
  1. Microdata / Schema.org JSON-LD blocks (`ratingValue`).
  2. Common Iranian scraper HTML classes (`.imdb_rate`, `.rate-score`, `span:contains('IMDb')`).
  3. Persian text patterns (e.g. `امتیاز: 7.8` or `IMDB: 7.8/10`).
  4. Parse and normalize to a standard `0.0 - 10.0` floating point value.
- When an IMDb score is missing or cannot be parsed, store `None`.
- Display logic:
  - If `imdb_rating` is present: Render badge with yellow star icon and formatted rating (e.g., `⭐ 7.8`).
  - If `imdb_rating` is `None`: Render subtle placeholder `—` or `بدون امتیاز` without layout shift.
  - Strictly DO NOT call external APIs (OMDb, TMDb) during scrapers or rendering.

**Rationale**:
- Adheres strictly to Constitution Principle II (Simplicity / YAGNI) and Principle IV (Offline Testability).
- Eliminates third-party API rate limits, external API keys, network overhead, and potential points of failure.

**Alternatives Considered**:
- *External API enrichment (e.g., OMDb / TMDb)*: Requires API keys, adds external network calls during search, slows down search response times, and fails in offline test fixtures.

---

### Decision 4: Client-Side Filter State & URL Synchronization

**Context**: Filter changes must feel instantaneous (sub-50ms) and allow users to share or bookmark filtered results.

**Decision**:
- Enhance `FilterState` in `apps/web/src/components/InViewFilterBar.tsx`:
  ```typescript
  export interface FilterState {
    qualities: string[]
    audioTracks: string[]
    sources: string[]
    accessTier: 'all' | 'free' | 'premium'
    censorship: 'all' | 'uncensored' | 'censored'
  }
  ```
- Use Next.js `useSearchParams` and `useRouter` / `window.history.replaceState` to sync `tier` and `censorship` query parameters without full page reload.
- Filter computation runs in-memory over the already fetched `MediaItem[]` array using React `useMemo`.

**Rationale**:
- Instantaneous UI response with zero backend round-trips.
- Clean URL shareability: `/?q=inception&tier=free&censorship=uncensored`.
