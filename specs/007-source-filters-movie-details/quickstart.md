# Quickstart & Verification Guide: Source Tier Filtering, Censorship Metadata, and IMDb Ratings

**Branch**: `007-source-filters-movie-details` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

This guide provides runnable scenarios and commands to verify that source tier filtering, censorship metadata, and IMDb rating badges function properly end-to-end.

---

## Prerequisites

1. Python 3.12+ virtual environment activated (`. .venv/bin/activate`).
2. Node.js 20+ and pnpm installed.
3. Dependencies installed (`pnpm install`).

---

## Scenario 1: Backend Domain Models & Scraper Parsing Verification

Verify that movie scrapers extract `imdb_rating`, `censorship_status`, and `source_access_tier` correctly, and that tests run offline with fixtures.

### Commands

```bash
# Run backend pytest suite focusing on movie scrapers and models
cd apps/api
pytest tests/ -k "movie or uptvs or doostihaa" -v
```

### Expected Outcome

1. All scraper tests pass using offline mocked fixtures (`respx`).
2. `MediaItem` instances contain:
   - Valid `imdb_rating` float (e.g. `7.8`) or `None`.
   - `censorship_status` matching expected values (`uncensored`, `censored`, `mixed`, or `unspecified`).
   - `source_access_tier` populated from `SourceConfig`.
3. `MovieDownloadVariant` instances declare `is_censored` and `is_premium` flags.

---

## Scenario 2: Web API Contract Verification

Verify that `GET /api/search?q=Inception&category=movies` returns the enhanced schema.

### Commands

```bash
# Start API in background (or run inline test)
python -m pytest apps/api/tests/test_search_api.py -v
```

### Expected Outcome

Search response items strictly validate against the schema in [contracts/media-search-api.json](contracts/media-search-api.json):
- Each item includes `imdb_rating`, `censorship_status`, and `source_access_tier`.
- Variants include `is_censored` and `is_premium`.

---

## Scenario 3: Frontend Component & In-View Filter Bar Unit Tests

Verify that `InViewFilterBar`, `MovieCard`, and `MovieDownloadMatrix` render correctly and filter items as specified.

### Commands

```bash
# Run web client tests
cd apps/web
pnpm test
```

### Expected Outcome

1. `InViewFilterBar` tests verify:
   - Toggling `tier: 'free'` filters out pure premium sources and strips VIP variants from freemium sources.
   - Toggling `censorship: 'uncensored'` filters out censored and unspecified items.
   - Reset button clears active filters.
2. `MovieCard` tests verify:
   - Star icon and IMDb rating score render when present; `—` placeholder renders when null.
   - Appropriate localized badge color tokens render for censorship statuses (`uncensored`, `censored`, `mixed`).
   - Source tier badge displays appropriately.

---

## Scenario 4: End-to-End Search & URL Filter Verification (Playwright)

Verify the complete user journey in the browser.

### Commands

```bash
# Run E2E test suite
pnpm exec playwright test e2e/specs/007-source-filters-movie-details.spec.ts
```

### Expected Outcome

1. User searches for a movie (e.g., "Inception").
2. Results grid displays movie cards with:
   - ⭐ IMDb score on top-right badge.
   - Censorship badge (نسخه کامل / بازبینی شده).
   - Source tier tag.
3. User clicks `فقط رایگان` (Free Only):
   - Grid updates instantly (< 50ms) without page reload.
   - URL updates to include `?tier=free`.
4. User clicks `بدون سانسور` (Uncensored Only):
   - Only verified uncensored movie cards remain visible.
   - URL updates to include `&censorship=uncensored`.
5. User refreshes the page:
   - Active filter chips and filtered results remain preserved from URL query parameters.
