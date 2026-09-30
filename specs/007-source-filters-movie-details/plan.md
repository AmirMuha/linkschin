# Implementation Plan: Source Tier Filtering, Censorship Metadata, and IMDb Ratings

**Branch**: `007-source-filters-movie-details` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-source-filters-movie-details/spec.md`

## Summary

Enhance media search and display with website access tier classification (Free vs. Premium vs. Freemium), censorship metadata extraction and strict verification filtering (Uncensored vs. Censored), and IMDb rating badges on movie cards. 

All metadata is extracted directly during scraper execution from upstream HTML and schema markup without introducing external third-party lookup APIs. Filtering is executed client-side over fetched results for sub-50ms responsiveness and synchronized to browser URL parameters (`tier`, `censorship`).

## Technical Context

**Language/Version**: Python 3.12 (Backend `apps/api`), TypeScript 5.6+ / Node.js 20+ (Frontend `apps/web`)

**Primary Dependencies**: FastAPI, Pydantic, Uvicorn, Next.js 15, React 19, Tailwind CSS, Lucide React

**Storage**: In-memory TTL cache (`apps/api/models.py`) and SQLite FTS5 (existing platform cache); no external databases

**Testing**: `pytest` plus an offline fixture runner (`apps/api/tests/run_all.py`), both reading static HTML fixtures from `apps/api/tests/fixtures/` (backend scrapers, db & API); `node --test` over `src/lib/*.test.ts` (frontend filter/URL logic, plain TS — no component test runner); Playwright (E2E)

**Target Platform**: Linux server / Modern Web Browsers (Desktop & Mobile)

**Project Type**: Monorepo Web Application (FastAPI backend + Next.js frontend)

**Performance Goals**: < 50ms client-side filter updates; zero latency overhead on scraper searches; zero layout shift on card rendering

**Constraints**: Zero new external runtime dependencies; strict compliance with Constitution Principle II (Simplicity / YAGNI), Principle III (No Media Relaying), and Principle IV (Offline Verification)

**Scale/Scope**: 2 movie scraper plugins updated (uptvs, doostihaa) + tier declarations in the source registry and SQLite persistence, ~3 frontend components enhanced (`InViewFilterBar`, `MovieCard`, `MovieDownloadMatrix`) with 2 new pure-lib modules (`filters.ts`, `urlFilters.ts`), 2 new URL query parameters

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Principle I: Library / Module Isolation**: PASS. Each movie scraper under `apps/api/sources/movies/` extracts censorship and IMDb scores independently using its own HTML parsing logic without depending on sibling scrapers.
- [x] **Principle II: Simplicity / YAGNI & Monorepo Platform Structure**: PASS. Zero external third-party metadata APIs (no OMDb/TMDb keys or network hops); ratings and censorship tags are scraped directly from existing source pages. Client-side filtering uses native React state without redundant backend round-trips.
- [x] **Principle III: No Media Relaying**: PASS. Aggregator handles only metadata (tier, censorship, IMDb rating) and direct links; no audio or video payloads are proxied or buffered.
- [x] **Principle IV: Testability & Offline Verification**: PASS. Scraper parsing logic for IMDb scores, censorship status, and access tiers is tested offline against the static HTML fixtures in `apps/api/tests/fixtures/` (no network mocking required).

## Project Structure

### Documentation (this feature)

```text
specs/007-source-filters-movie-details/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output: Technical decisions & rationale
├── data-model.md        # Phase 1 output: Schema & entity model
├── quickstart.md        # Phase 1 output: Runnable validation scenarios
├── checklists/          # Requirements & quality checklists
│   └── requirements.md
└── contracts/           # Phase 1 output: Interface & UI contracts
    ├── media-search-api.json
    └── ui-filter-contract.md
```

### Source Code (repository root)

```text
apps/api/
├── models.py                           # SourceAccessTier, CensorshipStatus enums; MediaItem, MovieDownloadVariant extensions
├── db.py                               # New columns + idempotent _migrate() so cached loads round-trip the metadata
├── sources/
│   ├── __init__.py                     # SourceConfig declarations with access_tier (uptvs=FREE, doostihaa=FREEMIUM)
│   └── movies/
│       ├── uptvs.py                    # Censorship, VIP & IMDb rating parsers (card-scoped '/10')
│       └── doostihaa.py                # Censorship, VIP & IMDb rating parsers (entity-decoded 'از 10')
├── web/
│   └── app.py                          # GET /api/sources emits access_tier; asdict search payload
└── tests/
    ├── test_movies_scrapers.py         # Offline fixture tests for ratings, tiers, and censorship derivation
    ├── test_db.py                      # SQLite round-trip + pre-007 schema migration tests
    └── test_sources_config.py          # Registry tier assertions

apps/web/
├── src/
│   ├── types/
│   │   └── media.ts                    # SourceAccessTier, CensorshipStatus, MediaItem & MovieDownloadVariant type extensions
│   ├── lib/
│   │   ├── filters.ts                  # Pure tier/censorship item & variant predicates
│   │   ├── urlFilters.ts               # URL <-> filter state (parseTierParam/parseCensorshipParam/buildSearchParams)
│   │   ├── filters.test.ts             # Predicate tests (node --test)
│   │   └── urlFilters.test.ts          # URL round-trip / default-omission tests (node --test)
│   ├── app/
│   │   └── page.tsx                    # Filter wiring, URL seeding/sync, empty-filtered-results panel
│   └── components/
│       ├── InViewFilterBar.tsx         # Access tier & censorship filter chips with reset action
│       └── cards/
│           ├── MovieCard.tsx           # IMDb rating badge, censorship badge, source tier tag
│           └── MovieDownloadMatrix.tsx # Variant-level censorship and VIP tags; row pruning via filters.ts
```

**Structure Decision**: Standard monorepo extension directly modifying existing packages (`apps/api` and `apps/web`). No new directories, services, or microservices are added.

## Complexity Tracking

*No violations. All design choices strictly adhere to the Constitution and minimal-dependency rules.*
