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

# Full offline verification without pytest (stdlib runner, no network)
python tests/run_all.py
```

### Expected Outcome

1. All scraper tests pass against the static offline fixtures in `tests/fixtures/`.
   Measured (2026-09-30): `python tests/run_all.py` = **60 passed / 0 failed**;
   `pytest tests/` = **65 passed**.
2. `MediaItem` instances contain:
   - Valid `imdb_rating` float (e.g. `7.9`) or `None`.
   - `censorship_status` matching expected values (`uncensored`, `censored`, `mixed`, or `unspecified`).
   - `source_access_tier` populated from `SourceConfig` (uptvs `free`, doostihaa `freemium`).
3. `MovieDownloadVariant` instances declare `is_censored` and `is_premium` flags.
   Note: every `is_premium` flag is `False` in the current recorded fixtures (no
   fixture carries a real VIP link — see research.md Implementation notes #4).
4. The SQLite round-trip holds: new fields survive `db.upsert_items` → `db.search`
   (`test_db.py`), and `_migrate()` upgrades pre-007 databases without error.

---

## Scenario 2: Web API Contract Verification

Verify that `GET /api/search?q=Inception&category=movies` returns the enhanced schema, and that `GET /api/sources` (no `/status` suffix) emits `access_tier` per source.

### Commands

```bash
# From apps/api
python -m pytest tests/test_api_search.py -v
```

### Expected Outcome

Search response items (`dataclasses.asdict` serialization) carry every contract field:
- Each item includes `imdb_rating`, `censorship_status`, and `source_access_tier` (enums serialize as bare strings since both are `str` subclasses).
- Variants include `is_censored` and `is_premium`.

---

## Scenario 3: Frontend Filter-Layer Unit Tests

Verify the pure filter/URL logic behind `InViewFilterBar`, `MovieCard`, and
`MovieDownloadMatrix`. The web package tests plain TS via `node --test` — there are no
component-render tests (no Vitest/RTL configured).

### Commands

```bash
# Run web client tests
cd apps/web
pnpm test            # or: node --test src/lib/*.test.ts
./node_modules/.bin/tsc --noEmit
```

### Expected Outcome

Measured (2026-09-30): **17 tests pass** with `node --test src/lib/*.test.ts`
(3 pre-existing `archive.test.ts` + 14 new: 8 in `filters.test.ts`, 6 in
`urlFilters.test.ts`); **`tsc --noEmit` = 0 errors** (`allowImportingTsExtensions: true`
in `apps/web/tsconfig.json` enables the `.ts`-extension imports the test files use).

1. `filters.test.ts` verifies:
   - `itemMatchesTier`: `free` keeps `free`+`freemium` and drops `premium` (and vice-versa); `all` is an identity pass-through.
   - `variantsForTier`: `free` hides `is_premium` rows; `premium` hides non-premium rows.
   - `itemMatchesCensorship`: strict filters keep `mixed`, drop `unspecified` (never coerced).
   - `variantsForCensorship`: rows with `is_censored == null` are hidden under either strict filter.
2. `urlFilters.test.ts` verifies: parsers reject non-permitted values (incl. `mixed`) with fallback to `all`; `buildSearchParams` omits defaults, preserves `q`/`category`, and round-trips through the parsers.
3. Badge rendering (`MovieCard`) is asserted through the e2e journey (Scenario 4, pending), not unit tests: IMDb `7.9`-style star badge or `—`, censorship pill per status (including neutral `نامشخص`), tier pill (`رایگان`/`ترکیبی`/`VIP`).

---

## Scenario 4: End-to-End Search & URL Filter Verification (Playwright) — Not Yet Green for 007

**Status (2026-09-30, measured)**: the spec-007 Playwright specs (T027) are NOT yet
created and `node e2e/check-coverage.mjs --check` still exits **1** overall — due to
pre-existing unmapped specs 002–004, not 007. Acceptance for this feature is "zero
`007-` prefixed gaps in its output" (currently true only because 007 is not yet in the
gate's `SPECS` list — e2e/specs/ contains only `001-mvp/`).

Expected journey once `e2e/specs/007-source-filters-movie-details/` exists (assertions
must come from what the recorded fixtures produce, e.g. IMDb `7.9` on the first card;
the censorship positive path exists only on doostihaa item enrichment):

1. User searches for a movie (e.g., "Inception").
2. Results grid displays movie cards with:
   - ⭐ IMDb score badge (bottom-start of the poster overlay, `7.9`-style or `—`).
   - Censorship badge (نسخه کامل / بازبینی شده / شامل هر دو نسخه / نامشخص).
   - Source tier tag (رایگان / ترکیبی / VIP).
3. User clicks `فقط رایگان` (Free Only):
   - Grid updates instantly (< 50ms) without page reload.
   - URL updates to include `?tier=free`.
4. User clicks `بدون سانسور` (Uncensored Only):
   - Only verified uncensored (or mixed) movie cards remain visible; `unspecified` items are dropped.
   - URL updates to include `&censorship=uncensored`.
5. User refreshes the page:
   - Active filter chips and filtered results remain preserved from URL query parameters
     (`page.tsx` mount effect seeds state from `parseTierParam`/`parseCensorshipParam`).
