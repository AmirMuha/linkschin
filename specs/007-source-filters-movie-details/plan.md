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

**Testing**: `pytest` with `respx` offline fixtures (backend scrapers & API), Vitest / React Testing Library (frontend components), Playwright (E2E)

**Target Platform**: Linux server / Modern Web Browsers (Desktop & Mobile)

**Project Type**: Monorepo Web Application (FastAPI backend + Next.js frontend)

**Performance Goals**: < 50ms client-side filter updates; zero latency overhead on scraper searches; zero layout shift on card rendering

**Constraints**: Zero new external runtime dependencies; strict compliance with Constitution Principle II (Simplicity / YAGNI), Principle III (No Media Relaying), and Principle IV (Offline Verification)

**Scale/Scope**: ~4 scraper plugins updated, ~3 frontend components enhanced (`InViewFilterBar`, `MovieCard`, `MovieDownloadMatrix`), 2 new URL query parameters

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Principle I: Library / Module Isolation**: PASS. Each movie scraper under `apps/api/sources/movies/` extracts censorship and IMDb scores independently using its own HTML parsing logic without depending on sibling scrapers.
- [x] **Principle II: Simplicity / YAGNI & Monorepo Platform Structure**: PASS. Zero external third-party metadata APIs (no OMDb/TMDb keys or network hops); ratings and censorship tags are scraped directly from existing source pages. Client-side filtering uses native React state without redundant backend round-trips.
- [x] **Principle III: No Media Relaying**: PASS. Aggregator handles only metadata (tier, censorship, IMDb rating) and direct links; no audio or video payloads are proxied or buffered.
- [x] **Principle IV: Testability & Offline Verification**: PASS. Scraper parsing logic for IMDb scores, censorship status, and access tiers is tested offline against static HTML fixtures using `respx`.

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
├── sources/
│   ├── __init__.py                     # SourceConfig declarations with access_tier
│   └── movies/
│       ├── uptvs.py                    # Censorship & IMDb rating parser extensions
│       └── doostihaa.py                # Censorship & IMDb rating parser extensions
└── tests/
    └── test_movie_sources.py           # Offline scraper fixture tests for ratings, tiers, and censorship

apps/web/
├── src/
│   ├── types/
│   │   └── media.ts                    # SourceAccessTier, CensorshipStatus, MediaItem & MovieDownloadVariant type extensions
│   └── components/
│       ├── InViewFilterBar.tsx         # Access tier & censorship filter chips with reset action
│       ├── cards/
│       │   ├── MovieCard.tsx           # IMDb rating badge, censorship badge, source tier tag
│       │   └── MovieDownloadMatrix.tsx # Variant-level censorship and VIP tags; filter refinement
│       └── SearchBar.tsx               # (Unchanged or URL sync coordination)
└── tests/
    └── components/
        └── InViewFilterBar.test.tsx    # Filter behavior tests
```

**Structure Decision**: Standard monorepo extension directly modifying existing packages (`apps/api` and `apps/web`). No new directories, services, or microservices are added.

## Complexity Tracking

*No violations. All design choices strictly adhere to the Constitution and minimal-dependency rules.*
