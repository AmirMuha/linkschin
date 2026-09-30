# Implementation Plan: Movie Source Expansion (20 Requested Sites)

**Branch**: `005-movie-source-expansion` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-movie-source-expansion/spec.md`

## Summary

Register 19 new movie/series sources (UpTV is already live) behind the existing `SourcePlugin`
protocol, add a `watch_url` result field so subscription services return a legitimate watch
destination instead of a download, and add per-source health tracking with a circuit breaker so a
dead or silently-broken source degrades visibly rather than blocking or hollowing out search.

Technical approach: extend the existing `SourceConfig.base_urls` list to be *iterated* (primary
plus ordered fallbacks) rather than read only at index 0, add an in-process health registry keyed by
source id, and write one parser per site against a stored HTML fixture. **No declarative pattern
engine** — see the FR-022 conflict below.

## Technical Context

**Language/Version**: Python 3.11+ (API); TypeScript 5.7 / Next.js 15.2 / React 19 (web)

**Primary Dependencies**: FastAPI ≥0.110, httpx ≥0.27, selectolax ≥0.3.21, cachetools ≥5.3.3,
SQLite (FTS5); web: next 15.2, react 19, tailwindcss 3.4, lucide-react

**Storage**: SQLite at `apps/api/data/index.db` (FTS5 + per-source state tables); in-memory TTL
cache (`cachetools`)

**Testing**: pytest 8 + pytest-asyncio (`asyncio_mode = "auto"`) + respx; offline runner
`python tests/run_all.py`; web: `node --test`; e2e: Playwright

**Target Platform**: Linux server, local development

**Project Type**: Turborepo monorepo — Python web-service backend + Next.js web client

**Performance Goals**: ≤10s end-to-end search latency with 24 registered sources; ≤7s per source;
each search must return from healthy sources even when others hang

**Constraints**: Persian/Arabic NFKC normalization on all queries; no media payload ever passes
through the server; offline-verifiable test suite with zero network dependency; no dependency
additions — everything needed is already installed

**Scale/Scope**: 20 requested sites (19 new, 1 already live), expanding the movie source set from
4 to 23 registered; ~20 new parser modules plus fixtures

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| **I. Library / Module Isolation** | PASS | Each new site is a standalone module under `apps/api/sources/movies/`, depending on no sibling scraper. Shared helpers come only from `sources/base.py`, which is exactly the existing convention. |
| **II. Simplicity / YAGNI** | **VIOLATION — justified** | FR-022 (clarified) requires a general declarative "standard site pattern" engine. Live fingerprinting showed only 3 of 16 probed sites run WordPress, and `?s=` search is unreliable even on WordPress. Building a general pattern engine would be speculative. See Complexity Tracking and the FR-022 conflict below. |
| **III. No Media Relaying** | PASS | No design change touches payload transport. `watch_url` points at the upstream site's own page; the server never proxies, buffers, or unlocks. R-007 records the no-bypass boundary explicitly. |
| **IV. Testability & Offline Verification** | PASS | Every new source ships a search + item HTML fixture verified through respx, matching the existing `conftest.py` convention. Sites that could not be reached get registry/state tests only — an accepted, recorded gap. |
| **Quality Gates: Unicode normalization** | PASS | Normalization is applied once in `normalize_persian_text` before dispatch, so all 19 new sources inherit it. No per-plugin work. |
| **Quality Gates: timeout budget** | PASS | 7s per source / 10s per search retained. The circuit breaker is what keeps a dead source from consuming its full 7s, protecting the 10s global budget at 6x source count. |

**Gate result**: PASS with one justified Principle II violation, recorded below rather than
silently ignored.

## FR-022 Conflict — requires a spec decision before tasks

Phase 0 research (R-002) found that the declarative pattern engine promised by FR-022 is not
justified by the actual sites: **3 of 16** fingerprinted sites run WordPress, and a `?s=` search URL
is a soft-404 returning byte-identical output to the homepage on at least two of them.

The plan below **narrows FR-022 to what the evidence supports**: a new site is registered by
configuration (addresses, category, watch-only flag) with no new code *when a parser for its shape
already exists*. Per-site parsers handle the rest. This keeps the user-visible promise that matters
— domain changes need no redeploy — while dropping an abstraction 3 sites do not justify.

**This is a spec change, not a silent plan change.** Options are put to the user in the completion
report before tasks are generated.

## Project Structure

### Documentation (this feature)

```text
specs/005-movie-source-expansion/
├── plan.md              # This file
├── spec.md              # Feature specification (clarified)
├── research.md          # Phase 0 output — live site measurements
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
apps/api/
├── models.py                     # + watch_url on MediaItem; + source health state
├── sources/
│   ├── __init__.py               # DEFAULT_CONFIGS + registry: 19 new entries,
│   │                             #   multi-address iteration, circuit breaker
│   ├── base.py                   # existing shared helpers (unchanged)
│   ├── health.py                 # NEW — per-source health state registry
│   └── movies/
│       ├── __init__.py           # export new plugins
│       ├── uptvs.py              # existing (UpTV already live)
│       ├── doostihaa.py          # existing
│       └── <site>.py             # 19 NEW — one module per new site
├── db.py                         # + persist/restore watch_url, source health
├── web/app.py                    # + health in /api/sources and /api/health
└── tests/
    ├── conftest.py               # + fixture per new source
    ├── fixtures/<site>_search.html, <site>_item.html
    └── test_movies_scrapers.py   # + offline parser tests
    └── test_sources_config.py    # + registry, fallback, breaker tests

apps/web/src/
├── types/media.ts                # + watch_url, + source health types
├── components/cards/MovieCard.tsx        # watch-only rendering
└── components/SourceStatusBar.tsx        # + greyed-out inactive sources
```

**Structure decision**: Existing Turborepo monorepo layout retained. New code goes into the existing
`apps/api/sources/movies/` package rather than a new service — Principle I requires the plugins to
be decoupled, not relocated, and moving them would violate the module-isolation convention the four
existing sources already follow.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **Principle II (YAGNI)** — general declarative "standard site pattern" engine (FR-022) | FR-022 as clarified promises a new site can be added by declarative description alone, matched to a recognized pattern, with no custom code | Live fingerprinting (research.md R-002) found only **3 of 16** reachable sites run WordPress, and the `?s=` convention returns a 200 soft-404 byte-identical to the homepage on at least 2 of them (filmchiin.ir: 100774 B for both). A pattern engine would be used ~3 times and would still require per-site overrides for the other 13. **Plan narrows FR-022 to a declarative site profile (addresses, category, watch-only flag) plus per-site parsers.** Flagged to the user as a spec change; not applied unilaterally. |

## Phase 1 Artifacts

- `data-model.md` — `watch_url` field, source health state machine, registry schema changes
- `contracts/api-contract.md` — extended `/api/sources`, `/api/health`, `/api/search` shapes
- `quickstart.md` — runnable validation of a new source end-to-end, offline
