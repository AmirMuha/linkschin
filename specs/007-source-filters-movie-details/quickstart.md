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
   Measured (2026-09-30): `python tests/run_all.py` = **62 passed / 0 failed**;
   `pytest tests/` = **67 passed**.
2. `MediaItem` instances contain:
   - Valid `imdb_rating` float (e.g. `7.9`) or `None`.
   - `censorship_status` matching expected values (`uncensored`, `censored`, `mixed`, or `unspecified`).
   - `source_access_tier` populated from `SourceConfig` (uptvs `free`, doostihaa `freemium`).
3. `MovieDownloadVariant` instances declare `is_censored` and `is_premium` flags.
   Note: every `is_premium` flag is `False` in the current recorded fixtures (no
   fixture carries a real VIP link — see research.md Implementation notes #4).
4. The SQLite round-trip holds: new fields survive `db.upsert_items` → `db.search`
   (`test_db.py`), and `_migrate()` upgrades pre-007 databases without error.
   Measured (2026-09-30) against a copy of the populated `apps/api/data/index.db`:
   **65 rows preserved, `media_items` 16 → 19 columns**, no data loss. This matters
   because `_collect_items` serves repeat searches from SQLite *before* any scraper
   runs — without the migration every cached card would read back as
   `unspecified` / `free` / `—`.

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
3. Badge rendering (`MovieCard`) is asserted through the e2e journey (Scenario 4), not unit tests: IMDb `7.9`-style star badge or `—`, censorship pill per status (including neutral `نامشخص`), tier pill (`رایگان`/`ترکیبی`/`VIP`).

---

## Scenario 4: End-to-End Search & URL Filter Verification (Playwright) — Green for 007

**Status (2026-09-30, measured)**: the 16 spec-007 Playwright specs exist under
`e2e/specs/007-source-filters-movie-details/` and **pass** — the full hermetic-chromium
run is **20 passed** (4 pre-existing `001-mvp` + 16 new). 007 is registered in the gate's
`SPECS` map, and `node e2e/check-coverage.mjs --check` reports **zero `007-` prefixed
gaps**. The gate still exits 1 overall because specs 002–004 are unmapped — pre-existing,
not this feature.

Note for local runs: `playwright.config.ts` starts the web server on port 3000 with
`reuseExistingServer: !process.env.CI`, so a dev server already on 3000 (e.g. from the
main checkout) will be adopted silently and the specs will run against the wrong build.
Run with `CI=1` and a free port 3000.

Journey asserted (values grounded in the recorded fixtures):

1. User searches for a movie (e.g. "batman") — 28 cards render (18 uptvs + 10 doostihaa).
2. Each card shows:
   - ⭐ IMDb badge — 25 rated (4 at `7.9`, 1 at `6.0`), 3 unrated showing `—`.
   - Censorship badge — 23 `نامشخص`, 5 `بازبینی شده` (the doostihaa release tagged
     `نسخه سانسور شده`); the positive path exists only on doostihaa item enrichment.
   - Source tier tag — `رایگان` (uptvs) / `ترکیبی` (doostihaa).
3. User clicks `فقط رایگان` (Free Only):
   - Grid refines client-side; no new `/api/search` request fires (FR-011).
   - URL updates to include `?tier=free`.
4. User clicks `بدون سانسور` (Uncensored Only):
   - No fixture is verified uncensored, so the grid correctly empties and the
     `نتیجه‌ای با این فیلترها نیست` panel offers a 1-click reset. This is the spec's
     strict-verification rule working as designed, not a defect.
   - `سانسور شده` keeps exactly the 5 `بازبینی شده` cards, each row tagged.
5. User refreshes the page:
   - The query, tier, and censorship all replay from `?q=&tier=&censorship=` — the
     `page.tsx` mount effect seeds state and `handleSearch` re-runs.
