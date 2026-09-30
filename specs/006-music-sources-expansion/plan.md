# Implementation Plan: Music Source Expansion

**Branch**: `006-music-sources-expansion` | **Date**: 2026-09-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/006-music-sources-expansion/spec.md`

## Summary

Expand the aggregator's music catalogue from 2 sources to the 20 named in the request, split into two kinds:

- **11 full sources** (download portals publishing per-track audio file links) resolve to a playable stream plus labelled download options.
- **9 reference sources** (subscription services, licensed players, video platforms) are indexed and surfaced as link-outs only — no media extraction, no credentials, no player or download control.

The technical approach is additive and reuses every existing pattern: a `SourceKind` field on `SourceConfig` selects between a normal media-resolving plugin and a page-link-only plugin; ordering and per-user filtering land in the one function that already merges source results; degraded state is derived from a persisted per-source failure counter. No new framework, no new persistence layer, no new media kind.

## Technical Context

**Language/Version**: Python 3.11+ (project targets `>=3.11`; local interpreter is 3.14.7), TypeScript 5.x for the web client

**Primary Dependencies**: FastAPI, httpx, selectolax, cachetools, Jinja2 (backend); Next.js, Tailwind CSS (frontend, `apps/web`). No new dependency is introduced by this feature.

**Storage**: SQLite (`apps/api/data/index.db`) with FTS5 for persisted items; in-memory TTL cache (`cache.py`). This feature adds **no new tables and no new database** — a per-source failure counter rides in the existing store.

**Testing**: pytest + pytest-asyncio + respx (mocked HTTP), `poe test` / `poe test-offline`; Playwright in `e2e/` for the web surface

**Target Platform**: Linux server (local single-process deployment), browser client

**Project Type**: web-service (FastAPI backend + Next.js frontend in a Turborepo monorepo)

**Performance Goals**: A search across all enabled music sources returns its complete result set within 3 seconds when every source responds normally (SC-006). The existing 7s-per-source / 10s-global budget is retained and is the binding constraint.

**Constraints**:
- No media may be buffered, proxied, or relayed through the server (Constitution Principle III, NON-NEGOTIABLE)
- Every source must verify offline against captured fixtures (Constitution Principle IV)
- No credentials stored, requested, or forwarded
- Persian/Arabic Unicode NFKC normalization on all search queries
- Adding sources must not regress movies/games/already-supported music (FR-028)

**Scale/Scope**: 20 new source configurations (11 full + 9 reference), 1 new enum, ~1 modified search function, ~2 modified web surfaces. Per-source result volume stays bounded by the existing `found[:5]` extraction cap.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status | Evidence |
|-----------|------|--------|----------|
| **I. Library/Module Isolation** | Every source is a standalone plugin; no scraper imports a sibling | **PASS** | Each new source is its own module under `apps/api/sources/music/`, importing only `sources.base` helpers. `SourceKind` is a shared enum on the data model, not a cross-scraper dependency. |
| **II. Simplicity / YAGNI & Monorepo Structure** | No new framework, DB, or broker; minimal dependencies | **PASS** | One enum, one registry list, one sort key, one client-side filter. No new package, no migration, no new endpoint. Degraded state reuses the existing SQLite store. |
| **III. No Media Relaying (NON-NEGOTIABLE)** | No media bytes traverse the server | **PASS** | Full sources emit upstream URLs only, as today. Reference sources emit a *page* URL and are structurally incapable of emitting media — enforced by their base class returning no stream and no downloads. |
| **IV. Testability & Offline Verification** | Every source verifiable with fixtures + respx, no network | **PASS** | Each source ships a captured fixture and a parser test. The reference-source base class is testable with no fixture at all. |

**Post-design re-check (Phase 1)**: all four still PASS. See "Constitution Re-check" below.

**Complexity Tracking**: empty — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/006-music-sources-expansion/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/api/
├── models.py                          # + SourceKind enum; SourceConfig gains `kind`
├── sources/
│   ├── base.py                        # + ReferenceSourcePlugin base protocol
│   ├── __init__.py                    # + 20 configs, kind-aware factory
│   └── music/
│       ├── reference.py               # NEW: shared page-link-only base class
│       ├── radiojavan.py              # NEW full
│       ├── musicdel.py                # NEW full
│       ├── musicfa.py                 # NEW full
│       ├── upsong.py                  # NEW full
│       ├── upmusics.py                # NEW full
│       ├── musictarin.py              # NEW full
│       ├── tehranmusic.py             # NEW full
│       ├── melodify.py                # NEW full
│       ├── takmusics.py               # NEW full
│       ├── one_rj.py                  # NEW full
│       ├── shenoto.py                 # NEW reference
│       ├── farsichart.py              # NEW reference
│       ├── aparat.py                  # NEW reference
│       ├── namasha.py                 # NEW reference
│       ├── rubika.py                  # NEW reference
│       ├── fam.py                     # NEW reference
│       ├── soundcloud.py              # NEW reference
│       ├── spotify.py                 # NEW reference
│       └── youtube_music.py           # NEW reference
├── web/
│   └── app.py                         # _collect_items: kind ordering + filter
├── db.py                              # + per-source failure counter
└── tests/
    ├── conftest.py                    # + reference-source fixtures
    ├── test_music_scrapers.py         # + new parser tests
    ├── test_reference_sources.py      # NEW: reference-source invariants
    ├── test_source_kind.py            # NEW: ordering + degraded threshold
    └── test_sources_config.py         # + 20-config registry assertions

apps/web/                              # source status display: kind badge, reason, filter UI
```

**Structure Decision**: The existing monorepo layout is kept. The only new shared abstraction is `sources/music/reference.py` — a base class for the 9 reference sources — because 9 near-identical plugins that differ only in URL and selector genuinely need a shared base. Eleven full sources stay standalone modules per Constitution Principle I, matching the existing `nex1music.py` / `popmusic.py` pattern exactly.

## Phase 0: Research Decisions

Full detail in [research.md](./research.md). Summary of the decisions that shape the design:

1. **How is `kind` represented?** An enum on `SourceConfig` with a `reference` boolean property, defaulted so existing configs are unchanged. Chosen over a bare bool to keep the value self-describing at call sites.
2. **How does a reference source avoid emitting media?** A dedicated base class whose `extract_links` is a no-op returning the item unchanged, and which is constructed so the media fields can never be populated. Enforced by test, not by convention.
3. **Where does kind ordering go?** One `sort` call in `_collect_items` after results are gathered — the single point where full and reference results first coexist.
4. **Where does per-user filtering go?** A query parameter consumed in `_collect_items` before plugins are selected. The chosen set is never cached, so the cache stays shared.
5. **How is "degraded" persisted?** A per-source failure counter in the existing SQLite store, incremented once per failed search, reset on any success. No new table.

## Phase 1: Design

Full detail in [data-model.md](./data-model.md), [contracts/](./contracts/), and [quickstart.md](./quickstart.md).

### Design highlights

- **`SourceKind`** — new enum (`full`, `reference`) on `SourceConfig`. Existing 8 configs are unaffected because the field defaults to `full`.
- **`ReferenceSourcePlugin`** — one base class covering all 9 link-out sources. Subclasses supply a search-URL builder and a result parser; the base supplies the "never emit media" guarantee.
- **Ordering** — a stable sort key on `MediaItem` placing full-source items ahead of reference-source items, applied once in `_collect_items` after the gather. Existing intra-group order is preserved because the sort is stable and the key is constant within a kind.
- **Per-user filter** — a repeated query parameter on `/search` and `/api/search`, applied before plugin selection. Deliberately *not* stored server-side, so no account or per-user table is needed.
- **Degraded state** — a per-source counter in the existing store, incremented on a failed search and reset on success. A source at 3 failures is excluded and reported.

### Constitution Re-check (post-design)

| Principle | Status | Note |
|-----------|--------|------|
| I. Module Isolation | PASS | `reference.py` is a base class in the same category package, not a cross-scraper import. Full sources remain independent of each other. |
| II. Simplicity / YAGNI | PASS | Total new surface: 1 enum, 1 base class, 1 sort key, 1 query param, 1 counter. No new table, no new endpoint, no new dependency, no new media kind. |
| III. No Media Relaying | PASS | The reference base class makes emitting media structurally impossible rather than merely discouraged — the strongest form of this guarantee available without a proxy in the path. |
| IV. Offline Verification | PASS | Reference sources are verifiable with a synthetic page; full sources each ship a captured fixture. The whole suite runs with no network. |

## Complexity Tracking

Empty — no constitution violations requiring justification.

## Out of Scope for Planning

Recorded here so `/speckit-tasks` does not drift into them:

- No per-source enable/disable UI for maintainers (the registry file remains the mechanism); only the *user-facing* hide filter from FR-029 is built.
- No ranking, scoring, or deduplication across sources beyond the existing behaviour — the same recording on two sites stays two results, per FR-004.
- No lyrics, no playlists, no podcasts, no video variant.
- No live re-verification harness. Captures are performed once during implementation and committed as fixtures; ongoing monitoring is out of scope per the spec.
