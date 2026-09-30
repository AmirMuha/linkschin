---
description: "Task list for Source Tier Filtering, Censorship Metadata, and IMDb Ratings"
---

# Tasks: Source Tier Filtering, Censorship Metadata, and IMDb Ratings

**Input**: Design documents from `specs/007-source-filters-movie-details/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. Constitution Principle IV requires offline fixture verification, and
quickstart.md defines 4 runnable scenarios.

**Organization**: Tasks are grouped by user story so each story can be implemented,
tested, and shipped independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g. US1, US2, US3)
- Include exact file paths in descriptions

### Corrections from reconnaissance (2026-09-30, post-task-generation)

1. **No fixture enrichment.** The recorded fixtures already contain everything this feature
   parses: `uptvs_search.html` has a plain-ASCII IMDb score (`7.9 /10` after
   `<i class="ficon-imdb">`) on 15/15 cards; `doostihaa_search.html` has `امتیاز: 7.9 از 10`
   on 10/10 articles (HTML-entity-encoded — requires `html.unescape` before regexing);
   `doostihaa_item.html` contains `نسخه سانسور شده` twice. Do NOT edit the fixtures —
   the 001 e2e spec pins assertions to them.
2. **JSON-LD `aggregateRating` is NOT IMDb.** uptvs item pages report `ratingValue: 83` on a
   0–100 scale; doostihaa reports `ratingValue: 5` on a 1–5 scale. These are site-user scores.
   Map to `imdb_rating` ONLY the `/10` and `از 10` forms.
3. **`censorship_status` is item-page-only and sparse.** uptvs fixtures have zero censorship
   markers (every uptvs item stays `unspecified`); doostihaa carries `نسخه سانسور شده` on the
   item page only, so search-list results are `unspecified` until `extract_links` runs. That is
   the spec's strict-verification behaviour, not a bug.
4. **Persistence is in scope (was missing).** `apps/api/web/app.py:64` serves repeat searches
   from SQLite via `db.search` → `db.py:_rehydrate`, which drops any field it has no column
   for. Without T005 below, every cached result renders `unspecified`/`free`/`unrated`.
5. **No VIP/freemium markup exists in any fixture.** `is_premium` can only be set from
   `SourceConfig.access_tier` plus keyword detection on label text (`VIP`, `اشتراکی`/`اشتراکی`);
   fixture-driven tests must cover the flag plumbing via unit-level variant construction, and
   freemium filtering is proven by predicate tests, not fixtures.
6. **Test discovery constraint**: new functions in `apps/api/tests/test_movies_scrapers.py`
   may only use parameter names present in `run_all.py`'s `fix_map` (the four movie fixture
   names) plus `monkeypatch`, or the offline runner silently passes `None`.
7. **Baselines** (verified): `apps/api` — 48/48 offline runner, 53 passed pytest;
   `apps/web` — 3/3 `node --test`, `tsc --noEmit` clean; `node e2e/check-coverage.mjs --check`
   already exits 1 with `FRs 5/73 US 2/18 AC 4/61` (specs 002–004 unmapped — pre-existing,
   not ours). Gate acceptance for this feature: zero `007-` prefixed gaps in its output.

---

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: Enums, model fields, persistence, and the shared vocabulary every story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T001 [P] Add `SourceAccessTier` enum (`free`, `premium`, `freemium`) and `CensorshipStatus` enum (`uncensored`, `censored`, `mixed`, `unspecified`) as `str, Enum` in `apps/api/models.py`, following the existing `Category` enum pattern; extend `SourceConfig` with `access_tier: SourceAccessTier = SourceAccessTier.FREE`, `MovieDownloadVariant` with `is_censored: bool | None = None` and `is_premium: bool = False`, and `MediaItem` with `imdb_rating: float | None = None`, `censorship_status: CensorshipStatus = CensorshipStatus.UNSPECIFIED`, `source_access_tier: SourceAccessTier = SourceAccessTier.FREE`. Field order must keep existing default-less fields first (dataclass `slots=True`); all new fields take defaults so existing construction sites (`db.py:_rehydrate`, tests) stay valid.
- [x] T002 [P] Add `export type SourceAccessTier = 'free' | 'premium' | 'freemium'`, `export type CensorshipStatus = 'uncensored' | 'censored' | 'mixed' | 'unspecified'`, the three `MediaItem` fields, the two `MovieDownloadVariant` fields (`is_censored?: boolean | null`, `is_premium?: boolean`), and `access_tier: SourceAccessTier` on `SourceStatus` in `apps/web/src/types/media.ts`.
- [x] T003 Declare `access_tier=` explicitly on every `SourceConfig` in `DEFAULT_CONFIGS` in `apps/api/sources/__init__.py` (movies, games, music), so tiers are greppable and the registry is self-documenting. uptvs/doostihaa are `freemium` per research.md Decision 1 (VIP-limited rows exist on their item pages); mirror/registry sources default `free` unless their known access model says otherwise.
- [x] T004 Add `"access_tier": s.access_tier.value` to the response dict in `list_sources()` in `apps/api/web/app.py` so the frontend `SourceStatusBar` receives the tier. Search item serialization already uses `asdict(item)` — the new dataclass fields serialize automatically (both enums are `str` subclasses, so JSON encodes bare values).
- [x] T005 Persist the new fields in `apps/api/db.py` (the cached-load blocker): add `imdb_rating REAL`, `censorship_status TEXT`, `source_access_tier TEXT` columns to `media_items` in `SCHEMA`, add `is_censored INT`, `is_premium INT` to `download_variants`; add an idempotent column migration (PRAGMA table_info + `ALTER TABLE ADD COLUMN`) run from `connect()`, because `CREATE TABLE IF NOT EXISTS` never updates the existing `data/index.db` (21 live rows, old schema); write the new values in `upsert_items`/`_variant_rows` and read them back in `_rehydrate` into `MediaItem.imdb_rating` / `censorship_status` / `source_access_tier` (enum-construct from TEXT, tolerate NULL → defaults) and `MovieDownloadVariant.is_censored` / `is_premium`.
- [x] T006 [P] Create `apps/web/src/lib/urlFilters.ts` with pure `parseTierParam(raw: string | null): 'all' | 'free' | 'premium'`, `parseCensorshipParam(raw: string | null): 'all' | 'uncensored' | 'censored'`, and `buildSearchParams(tier, censorship): URLSearchParams` helpers. Non-permitted values fall back to `'all'`; default values are omitted from the URL. These own the contract from `contracts/ui-filter-contract.md` §1. Note: files in `apps/web/src/lib/` must import each other with explicit `.ts` extensions and must not use the `@/` alias (invisible to `node --test`).

**Checkpoint**: Foundation ready — user story implementation can begin.

---

## Phase 2: User Story 1 - Filtering Media Sources by Access Tier (Priority: P1) 🎯 MVP

**Goal**: Users filter the results grid to Free Only or Premium Only; freemium sources stay
visible but their VIP download rows are hidden under Free Only.

**Independent Test**: Run a search, select "فقط رایگان", and confirm every remaining card
comes from a `free` or `freemium` source, that freemium cards show only `is_premium: false`
rows, and that purely `premium` cards are gone.

### Tests for User Story 1 ⚠️ write first, confirm they fail

- [ ] T007 [P] [US1] Add tests asserting every `DEFAULT_CONFIGS` entry exposes a valid `SourceAccessTier` and both movie sources are `freemium`, in `apps/api/tests/test_sources_config.py`.
- [ ] T008 [P] [US1] Add a SQLite round-trip test in `apps/api/tests/test_db.py`: upsert a `MediaItem` carrying `imdb_rating=7.8`, `censorship_status=CensorshipStatus.UNCENSORED`, `source_access_tier=SourceAccessTier.PREMIUM` and variants with `is_censored`/`is_premium` set, then `db.search` it back and assert every field survived; also assert migrating an old-schema DB (columns absent) via `connect()` yields NULL→defaults instead of an OperationalError.
- [x] T009 [P] [US1] Add tests for the tier predicates — `free` keeps `free` and `freemium` items, drops `premium`; `premium` keeps `premium` and `freemium`; variant pruning drops `is_premium === true` rows under `free` and `is_premium === false` rows under `premium`; `'all'` passes everything through untouched — in `apps/web/src/lib/filters.test.ts`.

### Implementation for User Story 1

- [x] T010 [US1] Create `apps/web/src/lib/filters.ts` exporting `itemMatchesTier(item: MediaItem, tier: TierFilter): boolean` and `variantsForTier(variants: MovieDownloadVariant[], tier: TierFilter): MovieDownloadVariant[]` implementing the `accessTier` rows of the filter evaluation matrix in `data-model.md`. Return the input array untouched when `tier === 'all'`.
- [ ] T011 [US1] In `apps/api/sources/movies/uptvs.py` and `apps/api/sources/movies/doostihaa.py`, set `source_access_tier=self.config.access_tier` on every `MediaItem` built in `parse_search_results`, and `is_premium` on every `MovieDownloadVariant` built in `parse_item_page` — `True` when the link label/anchor text carries a VIP marker (`VIP`, `اختصاصی`, `اشتراکی`), else `False` for freemium sources. Each plugin owns its regexes — no cross-scraper helper import (Constitution Principle I).
- [ ] T012 [US1] Extend `FilterState` with `accessTier: 'all' | 'free' | 'premium'` and add the access-tier chip group (`دسترسی:` / `همه` / `فقط رایگان` cyan active / `فقط اشتراکی / VIP` amber active) to `apps/web/src/components/InViewFilterBar.tsx`. Include `accessTier` in `hasActiveFilters` and in `handleReset`.
- [ ] T013 [US1] Add the access tier badge to the poster overlay of `MovieCard` in `apps/web/src/components/cards/MovieCard.tsx`: `free` → `رایگان` default pill, `premium` → `bg-amber-500/20 text-amber-300 border-amber-500/40` `VIP`, `freemium` → `bg-cyan-500/20 text-cyan-300 border-cyan-500/40` `ترکیبی`. Use RTL logical properties (`start-*`/`end-*`) like existing badges.
- [ ] T014 [US1] Add an optional `activeTierFilter?: 'all' | 'free' | 'premium'` prop and a VIP tag on premium variant rows in `apps/web/src/components/cards/MovieDownloadMatrix.tsx`; rows with `is_premium === true` are hidden when `activeTierFilter === 'free'`, and rows with `is_premium === false` are hidden when `activeTierFilter === 'premium'`.
- [ ] T015 [US1] Wire `filters.accessTier` into the `filteredItems` `useMemo` and the `InViewFilterBar` props in `apps/web/src/app/page.tsx`, seed the initial value from `parseTierParam` on mount, and push `tier` into the URL via `buildSearchParams` on change using `window.history.replaceState` (no page reload). Also surface tier on the source rows in `apps/web/src/components/SourceStatusBar.tsx` next to the enabled pill.

**Checkpoint**: User Story 1 fully functional and independently verifiable — MVP scope.

---

## Phase 3: User Story 2 - Censorship Status Visibility and Filtering (Priority: P2)

**Goal**: Every movie card shows a censorship badge and download rows declare their own
censorship state; the `بدون سانسور` / `سانسور شده` filters exclude `unspecified` items.

**Independent Test**: Search, confirm badges render on every card, select `بدون سانسور`, and
confirm no `censored` or `unspecified` card survives while `mixed` cards show only their
uncensored rows.

### Tests for User Story 2 ⚠️ write first, confirm they fail

- [ ] T016 [P] [US2] Add censorship derivation tests in `apps/api/tests/test_movies_scrapers.py`: `doostihaa_item_html` parses to `censorship_status == CensorshipStatus.CENSORED` (the fixture's `نسخه سانسور شده` marker) with `is_censored=True` on matching variants; a synthetic page with both censored and uncensored labels yields `MIXED`; `uptvs_item_html` (no marker) yields `UNSPECIFIED`. Use only the four existing fixture parameter names plus `monkeypatch` (run_all.py constraint).
- [ ] T017 [P] [US2] Add tests for censorship predicates in `apps/web/src/lib/filters.test.ts`: `uncensored` keeps `uncensored` and `mixed` items, drops `censored` and `unspecified`; `censored` keeps `censored` and `mixed`, drops `uncensored` and `unspecified`; mixed items prune to the matching variant rows; rows with `is_censored == null` are hidden under either strict filter.

### Implementation for User Story 2

- [ ] T018 [US2] In `apps/api/sources/movies/uptvs.py` and `apps/api/sources/movies/doostihaa.py`, add censorship keyword detection: apply `html.unescape` to the page before matching (doostihaa entity-encodes Persian), test title/tags/variant labels for `نسخه کامل` / `بدون سانسور` (uncensored) and `بازبینی شده` / `سانسور شده` (censored), set `is_censored` per variant, and derive the item-level `censorship_status` per validation rule 2 in `data-model.md` (mixed flags → `MIXED`, all-censored → `CENSORED`, all-uncensored → `UNCENSORED`, else `UNSPECIFIED`). Keep the regexes and a small `derive_censorship_status(variants)` helper inside each plugin file — no shared scraper module (Constitution I).
- [x] T019 [US2] Add `itemMatchesCensorship(item, censorship)` and `variantsForCensorship(variants, censorship)` to `apps/web/src/lib/filters.ts`, short-circuiting on `'all'` like the tier predicates.
- [ ] T020 [US2] Add the censorship chip group (`سانسور:` / `همه` / `بدون سانسور` emerald active / `سانسور شده` amber active) to `apps/web/src/components/InViewFilterBar.tsx`, extend `FilterState` with `censorship: 'all' | 'uncensored' | 'censored'`, and include it in `hasActiveFilters` and `handleReset`.
- [ ] T021 [US2] Add the censorship badge to the `MovieCard` overlay in `apps/web/src/components/cards/MovieCard.tsx` using `data-model.md` tokens: `uncensored` → `bg-emerald-950/80 text-emerald-300 border-emerald-800/60` (`نسخه کامل`), `censored` → `bg-amber-950/80 text-amber-300 border-amber-800/60` (`بازبینی شده`), `mixed` → `bg-cyan-950/80 text-cyan-300 border-cyan-800/60` (`شامل هر دو نسخه`), `unspecified` → `bg-zinc-900/80 text-zinc-400` (`نامشخص`).
- [ ] T022 [US2] Add an optional `activeCensorshipFilter?: 'all' | 'uncensored' | 'censored'` prop and a per-row censorship tag to `apps/web/src/components/cards/MovieDownloadMatrix.tsx`; rows with `is_censored === true` hidden under `uncensored`, `is_censored === false` hidden under `censored`, `is_censored == null` hidden under either strict filter.
- [ ] T023 [US2] Wire `filters.censorship` into `filteredItems` in `apps/web/src/app/page.tsx`, pass both active filters into `MovieCard`→`MovieDownloadMatrix`, seed from `parseCensorshipParam` on mount, sync `censorship` into the URL, and add the empty-filtered-results panel (current empty state at `page.tsx:292` keys off `items.length === 0` only — add a `filteredItems.length === 0 && items.length > 0` branch with a 1-click reset that clears filters).

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 4: User Story 3 - IMDb Rating Display on Movie Cards (Priority: P3)

**Goal**: Each movie card shows a star badge with the IMDb score, or a `—` placeholder when
the source has none.

**Independent Test**: Search a well-known title, confirm `⭐ 7.8`-style badge on the overlay,
and confirm an unrated fixture renders `—` with no layout shift.

### Tests for User Story 3 ⚠️ write first, confirm they fail

- [ ] T024 [P] [US3] Add IMDb extraction tests in `apps/api/tests/test_movies_scrapers.py`: `parse_search_results(uptvs_search_html)` yields `imdb_rating == 7.9` on the first card (fixture-verified) and a non-None rating on all 15; `parse_search_results(doostihaa_search_html)` yields `imdb_rating == 7.9` on the first article; a synthetic card with no score yields `None`; scores parsed from `84%` normalize to `8.4`, out-of-range (>10) or NaN resolve to `None`; JSON-LD `aggregateRating` (83 or 5) is NOT used.

### Implementation for User Story 3

- [ ] T025 [US3] In `apps/api/sources/movies/uptvs.py`, extract per-card IMDb from the search page with a card-scoped regex on the existing `title=`-link iteration (score appears as `N.N /10` following `<i class="ficon-imdb">`); in `apps/api/sources/movies/doostihaa.py`, apply `html.unescape` to each `<article>` block then match `امتیاز[^0-9]{0,12}([0-9]+(?:\.[0-9]+)?)` and require a `از 10` or `/10` scale marker when present (a bare number defaults to the 10-scale). Store a float rounded to 1 decimal, or `None` when absent/malformed/out of `0.0`–`10.0` (validation rule 1). Never map JSON-LD `aggregateRating`. No external API calls.
- [ ] T026 [US3] Add the IMDb badge to the poster overlay of `MovieCard` in `apps/web/src/components/cards/MovieCard.tsx`: lucide `Star` with `fill-amber-400 text-amber-400 w-3 h-3`, text `item.imdb_rating?.toFixed(1) ?? '—'`, wrapped in `bg-zinc-950/80 border border-zinc-800/80 font-mono text-2xs text-amber-300 backdrop-blur-md px-2 py-0.5 rounded-full`. Render it unconditionally so the badge box never changes size (SC-002 zero layout shift). Position: bottom-end of the poster overlay (top-start and top-end are taken by Source and Year badges).

**Checkpoint**: All three stories independently functional.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [ ] T027 [US1][US2][US3] Add `{ id: '007', dir: '007-source-filters-movie-details' }` to the `SPECS` array in `e2e/check-coverage.mjs` and create `e2e/specs/007-source-filters-movie-details/us1-tiers.spec.ts`, `us2-censorship.spec.ts`, `us3-ratings.spec.ts` following `e2e/specs/001-mvp/us1-movies.spec.ts` exactly (import from `../../fixtures/app`, `test.describe('007 USn — …')`, titles tagged `[007-USn-ACm][FR-NNN]`). Cover all 10 acceptance scenarios; FR-011 (client-side) and FR-012 (URL restore on reload) are asserted by the tier/censorship specs. FR-001/FR-008/FR-009/FR-010 ride on existing scenario titles (multi-FR tags are allowed: `[FR-008][FR-009]`). Assertion values must come from what the recorded fixtures actually produce (IMDb 7.9 first card; censorship positive path only on doostihaa item enrichment). Note SC-001 (<50ms) is latency-class — add `007-SC-001: latency` to the `NOT_E2E` table.
- [ ] T028 [P] Run `pnpm --filter @repo/web test` (now includes `filters.test.ts` and `urlFilters` coverage inside `filters.test.ts` or its own file) and `tsc --noEmit` — error count must stay at 0.
- [ ] T029 [P] Run `node e2e/check-coverage.mjs --check` and confirm the output lists no `007-` gaps (overall exit stays 1 due to pre-existing 002–004 gaps — not our scope).
- [ ] T030 Run the full validation suite from the worktree root: `apps/api` offline runner (`python tests/run_all.py`) and pytest, `apps/web` `node --test`, Playwright hermetic run of `specs/007-source-filters-movie-details` (`playwright test specs/007-source-filters-movie-details`), and record outcomes against `specs/007-source-filters-movie-details/quickstart.md` scenarios 1–4.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: No dependencies — blocks all user stories
- **User Stories (Phases 2–4)**: All depend on Phase 1; proceed in parallel or priority order P1 → P2 → P3
- **Polish (Phase 5)**: Depends on all three stories

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 1. No dependency on US2/US3. Ships the MVP.
- **US2 (P2)**: Starts after Phase 1. Extends `filters.ts` / `InViewFilterBar` from US1 — merge after US1, do not edit those files concurrently.
- **US3 (P3)**: Starts after Phase 1. Shares the two scraper files and `MovieCard.tsx` with US1/US2 — run last or coordinate merges.

### Within Each User Story

- Tests written first must fail before implementation
- `filters.ts` before UI wiring; scraper parsing before card display; core before page integration

### Parallel Opportunities

- T001, T002, T006 in Phase 1 are different files
- T007, T008, T009 are different files; T016, T017 are different files; T024 independent
- Scraper tasks split by plugin (`uptvs.py` ↔ `doostihaa.py`) within T011/T018/T025
- T028 and T029 in Polish are independent

---

## Parallel Example: Phase 1

```bash
Task: "T001 models.py enums + fields"
Task: "T002 apps/web/src/types/media.ts extensions"
Task: "T006 apps/web/src/lib/urlFilters.ts"
# T003/T004/T005 touch registry/API/db — sequential after T001
```

## Parallel Example: User Story 1

```bash
# Tests first, three files, no shared state:
Task: "T007 [US1] apps/api/tests/test_sources_config.py"
Task: "T008 [US1] apps/api/tests/test_db.py"
Task: "T009 [US1] apps/web/src/lib/filters.test.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Foundational (T001–T006)
2. Phase 2: User Story 1 (T007–T015)
3. **STOP and VALIDATE**: Free Only / Premium Only filters work end-to-end, including cached loads
4. Ship the tier filter as the first release

### Incremental Delivery

1. Foundational → vocabulary + persistence locked
2. US1 → tier filtering + badges → ship
3. US2 → censorship strict filters + variant refinement → ship
4. US3 → IMDb badge + unrated fallback → ship
5. Polish → e2e gate, quickstart validation

---

## Notes

- [P] tasks = different files, no dependencies
- Each user story is independently completable and testable
- Verify tests fail before implementing; commit after each task or logical group
- `asdict()` serializes new dataclass fields automatically; `str`-sub enums encode as bare values
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
