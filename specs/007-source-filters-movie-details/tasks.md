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
- **[Story]**: User story this task belongs to (US1, US2, US3)
- Every task names its exact file path

### Deviations from plan.md (decided during task generation)

1. **Contract endpoint name.** `contracts/media-search-api.json` documents
   `/api/sources/status`, but the codebase serves `GET /api/sources`. We extend the
   existing route rather than adding a second alias.
2. **Frontend test runner.** plan.md assumed Vitest + React Testing Library. The repo has
   neither; `apps/web/package.json` runs `node --test src/lib/*.test.ts` and
   `src/lib/archive.test.ts` is the established pattern. Filter logic is therefore a pure
   module in `src/lib/` tested with `node --test`. No new dependency is added.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Shared test data that all three stories consume.

- [ ] T001 Enrich the four existing movie scraper fixtures with the metadata this feature parses — an embedded IMDb score, Persian censorship keywords (`نسخه کامل` / `بازبینی شده`), and for one freemium source a download row marked VIP — in `apps/api/tests/fixtures/uptvs_search.html`, `apps/api/tests/fixtures/uptvs_item.html`, `apps/api/tests/fixtures/doostihaa_search.html`, `apps/api/tests/fixtures/doostihaa_item.html`. Fixtures already load via `apps/api/tests/conftest.py`; no conftest change is needed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Enums, model fields, and the shared vocabulary every story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 [P] Add `SourceAccessTier` enum (`free`, `premium`, `freemium`) and `CensorshipStatus` enum (`uncensored`, `censored`, `mixed`, `unspecified`) as `str, Enum` in `apps/api/models.py`, following the existing `Category` enum pattern; extend `SourceConfig` with `access_tier: SourceAccessTier = SourceAccessTier.FREE`, `MovieDownloadVariant` with `is_censored: bool | None = None` and `is_premium: bool = False`, and `MediaItem` with `imdb_rating: float | None = None`, `censorship_status: CensorshipStatus = CensorshipStatus.UNSPECIFIED`, `source_access_tier: SourceAccessTier = SourceAccessTier.FREE`. Field order must keep existing default-less fields first (dataclass `slots=True`).
- [ ] T003 [P] Add `export type SourceAccessTier = 'free' | 'premium' | 'freemium'`, `export type CensorshipStatus = 'uncensored' | 'censored' | 'mixed' | 'unspecified'`, the three `MediaItem` fields, the two `MovieDownloadVariant` fields (`is_censored?: boolean | null`, `is_premium?: boolean`), and `access_tier: SourceAccessTier` on `SourceStatus` in `apps/web/src/types/media.ts`.
- [ ] T004 Declare `access_tier=` explicitly on every `SourceConfig` in `DEFAULT_CONFIGS` in `apps/api/sources/__init__.py` (both movie sources, both game sources, both music sources) instead of relying on the default, so tiers are greppable and the registry is self-documenting.
- [ ] T005 Add `"access_tier": s.access_tier.value` to the response dict in `list_sources()` in `apps/api/web/app.py` so the frontend `SourceStatusBar` receives the tier. Search item serialization already uses `asdict(item)` and needs no change — the new dataclass fields serialize automatically.
- [ ] T006 [P] Create `apps/web/src/lib/urlFilters.ts` with pure `parseTierParam(raw: string | null): 'all' | 'free' | 'premium'`, `parseCensorshipParam(raw: string | null): 'all' | 'uncensored' | 'censored'`, and `buildSearchParams(tier, censorship): URLSearchParams` helpers. Non-permitted values fall back to `'all'`. These own the URL contract from `contracts/ui-filter-contract.md` §1 (`tier` and `censorship`, default omitted).

**Checkpoint**: Vocabulary in place — user story implementation can begin.

---

## Phase 3: User Story 1 - Filtering Media Sources by Access Tier (Priority: P1) 🎯 MVP

**Goal**: Users filter the results grid to Free Only or Premium Only; freemium sources stay
visible but their VIP download rows are hidden under Free Only.

**Independent Test**: Run a search, select "فقط رایگان", and confirm every remaining card
comes from a `free` or `freemium` source, that freemium cards show only `is_premium: false`
rows, and that purely `premium` cards are gone.

### Tests for User Story 1 ⚠️ write first, confirm they fail

- [ ] T007 [P] [US1] Add tests asserting each `DEFAULT_CONFIGS` entry exposes a valid `SourceAccessTier` and that the two movie sources are declared as intended in `apps/api/tests/test_sources_config.py`.
- [ ] T008 [P] [US1] Add tests asserting freemium item pages yield variants with `is_premium=True` for VIP rows and `False` for free rows, and that premium sources yield `is_premium=True` throughout, in `apps/api/tests/test_movies_scrapers.py`.
- [ ] T009 [P] [US1] Add tests for the tier predicates — `free` keeps `free` and `freemium`, drops `premium`; `premium` keeps `premium` and `freemium`; variant pruning drops `is_premium === true` under `free` and drops `is_premium === false` under `premium` — in `apps/web/src/lib/filters.test.ts`.

### Implementation for User Story 1

- [ ] T010 [US1] Create `apps/web/src/lib/filters.ts` exporting `itemMatchesTier(item: MediaItem, tier: TierFilter): boolean` and `variantsForTier(variants: MovieDownloadVariant[], tier: TierFilter): MovieDownloadVariant[]` implementing the `accessTier` rows of the filter evaluation matrix in `data-model.md`. Return the input array untouched when `tier === 'all'`.
- [ ] T011 [US1] Set `source_access_tier` on every `MediaItem` and `is_premium` on every `MovieDownloadVariant` built in `apps/api/sources/movies/uptvs.py` and `apps/api/sources/movies/doostihaa.py`, sourced from each plugin's own `SourceConfig.access_tier` and from per-row VIP markers in the item HTML. Keep each plugin self-contained — no shared helper import between scrapers (Constitution Principle I).
- [ ] T012 [US1] Extend `FilterState` with `accessTier: 'all' | 'free' | 'premium'` and add the access-tier chip group (`دسترسی:` / `همه` / `فقط رایگان` cyan active / `فقط اشتراکی / VIP` amber active) to `InViewFilterBar` in `apps/web/src/components/InViewFilterBar.tsx`. Include `accessTier` in `hasActiveFilters` and in `handleReset`.
- [ ] T013 [US1] Add the access tier badge to the poster overlay of `MovieCard` in `apps/web/src/components/cards/MovieCard.tsx`: `free` → `رایگان`, `premium` → `bg-amber-500/20 text-amber-300 border-amber-500/40` `VIP`, `freemium` → `bg-cyan-500/20 text-cyan-300 border-cyan-500/40` `ترکیبی`.
- [ ] T014 [US1] Add an optional `activeTierFilter?: 'all' | 'free' | 'premium'` prop and a VIP tag on premium variant rows in `apps/web/src/components/cards/MovieDownloadMatrix.tsx`; rows with `is_premium === true` are hidden when `activeTierFilter === 'free'`, and rows with `is_premium === false` are hidden when `activeTierFilter === 'premium'`.
- [ ] T015 [US1] Wire `filters.accessTier` into the `filteredItems` `useMemo` and the `InViewFilterBar` props in `apps/web/src/app/page.tsx`, seed the initial value from `parseTierParam` on mount, and push `tier` into the URL via `buildSearchParams` on change (no page reload).

**Checkpoint**: User Story 1 fully functional and independently verifiable — MVP scope.

---

## Phase 4: User Story 2 - Censorship Status Visibility and Filtering (Priority: P2)

**Goal**: Every movie card shows a censorship badge and download rows declare their own
censorship state; the `بدون سانسور` / `سانسور شده` filters exclude `unspecified` items.

**Independent Test**: Search, confirm badges render on every card, select `بدون سانسور`, and
confirm no `censored` or `unspecified` card survives while `mixed` cards show only their
uncensored rows.

### Tests for User Story 2 ⚠️ write first, confirm they fail

- [ ] T016 [P] [US2] Add tests asserting censorship derivation in `apps/api/tests/test_movies_scrapers.py`: `نسخه کامل` markup yields `uncensored`, `بازبینی شده` yields `censored`, a page carrying both censored and uncensored variants yields `mixed`, and a page with no marker yields `unspecified`. Assert per-variant `is_censored` alongside the parent status.
- [ ] T017 [P] [US2] Add tests for censorship predicates in `apps/web/src/lib/filters.test.ts`: `uncensored` keeps `uncensored` and `mixed`, drops `censored` and `unspecified`; `censored` keeps `censored` and `mixed`, drops `uncensored` and `unspecified`; mixed items prune to the matching variant rows.

### Implementation for User Story 2

- [ ] T018 [US2] Add normalized Persian keyword regexes (`نسخه کامل`, `بدون سانسور`, `بازبینی شده`, `سانسور شده`) and a `derive_censorship_status(variants)` function implementing validation rule 2 in `data-model.md` inside `apps/api/sources/movies/uptvs.py`, and apply the equivalent logic in `apps/api/sources/movies/doostihaa.py`. Each scraper owns its own regexes; no cross-scraper helper module.
- [ ] T019 [US2] Create the censorship predicates `itemMatchesCensorship(item, censorship)` and `variantsForCensorship(variants, censorship)` in `apps/web/src/lib/filters.ts` using `variantsForTier`-style short-circuit on `'all'`.
- [ ] T020 [US2] Add the censorship badge group (`سانسور:` / `همه` / `بدون سانسور` emerald active / `سانسور شده` amber active) to `InViewFilterBar` in `apps/web/src/components/InViewFilterBar.tsx`, extend `FilterState` with `censorship: 'all' | 'uncensored' | 'censored'`, and include it in `hasActiveFilters` and `handleReset`.
- [ ] T021 [US2] Add the censorship badge to the overlay of `MovieCard` in `apps/web/src/components/cards/MovieCard.tsx` using the theme tokens from `data-model.md`: `uncensored` → `bg-emerald-950/80 text-emerald-300 border-emerald-800/60` (`نسخه کامل`), `censored` → `bg-amber-950/80 text-amber-300 border-amber-800/60` (`بازبینی شده`), `mixed` → `bg-cyan-950/80 text-cyan-300 border-cyan-800/60` (`شامل هر دو نسخه`), `unspecified` → neutral `bg-zinc-900/80 text-zinc-400` (`نامشخص`).
- [ ] T022 [US2] Add an optional `activeCensorshipFilter?: 'all' | 'uncensored' | 'censored'` prop and a per-row censorship tag to `MovieDownloadMatrix` in `apps/web/src/components/cards/MovieDownloadMatrix.tsx`; rows with `is_censored === true` are hidden under `uncensored`, rows with `is_censored === false` are hidden under `censored`, and rows with `is_censored == null` are hidden under either strict filter.
- [ ] T023 [US2] Wire `filters.censorship` into `filteredItems`, pass both active filters into `MovieCard` via `apps/web/src/app/page.tsx`, seed from `parseCensorshipParam` on mount, sync `censorship` into the URL, and render the empty-state panel with a 1-click filter reset when combined filters match nothing.

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - IMDb Rating Display on Movie Cards (Priority: P3)

**Goal**: Each movie card shows a star badge with the IMDb score, or a `—` placeholder when
the source has none.

**Independent Test**: Search a well-known title, confirm `⭐ 7.8`-style badge on the overlay,
and confirm an unrated fixture renders `—` with no layout shift.

### Tests for User Story 3 ⚠️ write first, confirm they fail

- [ ] T024 [P] [US3] Add tests for IMDb normalization in `apps/api/tests/test_movies_scrapers.py`: JSON-LD `ratingValue` yields the score, `امتیاز: 7.8` / `IMDB: 7.8/10` Persian text yields the score, `84%` normalizes to `8.4`, a score outside `0.0`–`10.0` yields `None`, and an unparseable string yields `None`.

### Implementation for User Story 3

- [ ] T025 [US3] Add IMDb extraction to `apps/api/sources/movies/uptvs.py` and `apps/api/sources/movies/doostihaa.py` — JSON-LD `ratingValue`, `.imdb_rate` / `.rate-score` class selectors, then the Persian text patterns — storing a float rounded to 1 decimal place, or `None` when absent, malformed, NaN, or out of the `0.0`–`10.0` range (validation rule 1 in `data-model.md`). No external API call.
- [ ] T026 [US3] Add the IMDb badge to the poster overlay of `MovieCard` in `apps/web/src/components/cards/MovieCard.tsx`: lucide `Star` with `fill-amber-400 text-amber-400 w-3 h-3`, text `item.imdb_rating.toFixed(1)` or `—`, wrapped in `bg-zinc-950/80 border border-zinc-800/80 font-mono text-2xs text-amber-300 backdrop-blur-md px-2 py-0.5 rounded-full`. Render it unconditionally so the badge box never changes size.

**Checkpoint**: All three stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T027 [P] Add the browser specs for this feature in `e2e/specs/007-source-filters-movie-details/`, reusing the `test` fixture from `e2e/fixtures/app.ts`: badges render on cards, `فقط رایگان` hides premium cards and VIP rows, `بدون سانسور` hides censored and unspecified cards, and a page reload restores both filters from the URL.
- [ ] T028 Run `node e2e/check-coverage.mjs` to regenerate `e2e/TRACEABILITY.md` and confirm the FR-001…FR-012 coverage gate exits zero.
- [ ] T029 Run `pnpm --filter @repo/web check` (`tsc --noEmit`) and fix any type errors introduced by T003.
- [ ] T030 Run the full quickstart validation — `pytest apps/api/tests -k "movie or uptvs or doostihaa or sources_config" -v`, `pnpm --filter @repo/web test`, and the e2e suite — and record the observed outcomes in `specs/007-source-filters-movie-details/quickstart.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Phase 1 — blocks all user stories
- **User Stories (Phase 3–5)**: All depend on Phase 2; stories can proceed in parallel or in priority order P1 → P2 → P3
- **Polish (Phase 6)**: Depends on all three stories

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2. No dependency on US2/US3. Ships the MVP.
- **US2 (P2)**: Starts after Phase 2. Extends `filters.ts` and `InViewFilterBar` from US1 — merge with US1 rather than working concurrently on those two files.
- **US3 (P3)**: Starts after Phase 2. Touches only `uptvs.py`, `doostihaa.py`, `MovieCard.tsx`. Shares the two scraper files and the card with US1/US2 — coordinate or run last.

### Within Each User Story

- Tests are written first and must fail before implementation
- Filters module before UI wiring
- Scraper parsing before card display
- Core implementation before page integration

### Parallel Opportunities

- T002, T003, T006 in Phase 2 are independent files
- T007, T008, T009 in US1 are independent files
- T016, T017 in US2 are independent files
- T011 within US1 splits cleanly by plugin: `uptvs.py` and `doostihaa.py`
- T018 within US2 splits the same way

---

## Parallel Example: User Story 1

```bash
# Tests first, three files, no shared state:
Task: "US1 source tier registry assertions in apps/api/tests/test_sources_config.py"
Task: "US1 freemium variant is_premium assertions in apps/api/tests/test_movies_scrapers.py"
Task: "US1 tier predicate tests in apps/web/src/lib/filters.test.ts"

# Scrapers split by plugin (both depend on T002):
Task: "US1 set is_premium + source_access_tier in apps/api/sources/movies/uptvs.py"
Task: "US1 set is_premium + source_access_tier in apps/api/sources/movies/doostihaa.py"
```

## Parallel Example: User Story 2

```bash
Task: "US2 censorship derivation tests in apps/api/tests/test_movies_scrapers.py"
Task: "US2 censorship predicate tests in apps/web/src/lib/filters.test.ts"

Task: "US2 censorship regexes + derive_censorship_status in apps/api/sources/movies/uptvs.py"
Task: "US2 censorship regexes + derive_censorship_status in apps/api/sources/movies/doostihaa.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup (T001)
2. Phase 2: Foundational (T002–T006)
3. Phase 3: User Story 1 (T007–T015)
4. **STOP and VALIDATE**: confirm the Free Only / Premium Only filters work end to end
5. Ship the tier filter as the first release

### Incremental Delivery

1. Setup + Foundational → vocabulary locked
2. US1 → tier filtering + tier badges → ship
3. US2 → censorship badges + strict filters + variant-level refinement → ship
4. US3 → IMDb badge with unrated fallback → ship
5. Polish → E2E, traceability, type check, quickstart validation

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Then: Developer A → US1 (`models`, `sources/__init__`, `web/app`, scrapers, filters, page);
   Developer B → US2 (`MovieDownloadMatrix`, `InViewFilterBar` censorship chips, `filters.ts` censorship predicates);
   Developer C → US3 (`MovieCard` IMDb badge, scraper IMDb parsing)
3. B and C must not edit `filters.ts`, `page.tsx`, or `MovieCard.tsx` concurrently with A — sequence those merges

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps a task to its user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
- `asdict()` in `apps/api/web/app.py` serializes the new dataclass fields automatically; both
  enums subclass `str`, so JSON encodes them as their bare values
