---

description: "Task list for Music Source Expansion"
---

# Tasks: Music Source Expansion

**Input**: Design documents from `/specs/006-music-sources-expansion/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. The spec's SC-004 makes "100% of new sources pass with no network" a hard gate, and Constitution Principle IV makes offline verification non-negotiable — so these are requirements, not optional extras.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Backend tasks use `apps/api/...`; web client tasks use `apps/web/...`. All paths are relative to the repository root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the no-regression baseline and prepare capture artefacts before any code changes.

- [ ] T001 Run the existing offline suite and record the baseline in the commit message: `cd apps/api && poe test-offline` — every test must pass before any change, since SC-010 requires no regression and this is the only way to prove it later
- [ ] T002 [P] Capture live search and item-page fixtures for each reachable full source into `apps/api/tests/fixtures/<source_id>_search.html` and `<source_id>_item.html`, following the naming of the existing `nex1music_search.html` / `nex1music_item.html` pair
- [ ] T003 [P] Extend the `SourceStatus` interface in `apps/web/src/types/media.ts` with four optional fields — `kind?: string`, `status?: string`, `inactive_reason?: string | null`, `consecutive_failures?: number` — marked optional so an older server response still type-checks (contract G4)

**Checkpoint**: Baseline recorded, fixtures captured, client types tolerant of the new fields.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 [P] Add `SourceKind` enum (`FULL = "full"`, `REFERENCE = "reference"`) and a `kind: SourceKind = SourceKind.FULL` field plus an `is_reference` read-only property to `SourceConfig` in `apps/api/models.py` — the default MUST be `SourceKind.FULL` so all 6 existing `SourceConfig(...)` call sites keep working unchanged (FR-028)
- [ ] T005 [P] Add `consecutive_failures INTEGER NOT NULL DEFAULT 0` to the `crawl_state` table in `apps/api/db.py` via a guarded `ALTER TABLE` that first checks `PRAGMA table_info(crawl_state)` — the schema is created with `CREATE TABLE IF NOT EXISTS`, so editing that string adds the column to no existing database (see quickstart troubleshooting)
- [ ] T006 [P] Add `get_consecutive_failures(source_id) -> int`, `record_search_failure(source_id) -> int`, and `record_search_success(source_id) -> None` to `apps/api/db.py`, modelled on the existing `get_last_page` / `set_last_page` pair
- [ ] T007 Create `ReferenceSourcePlugin` base class in `apps/api/sources/music/reference.py` with a no-op `extract_links` that returns the item unchanged and has no code path that populates `stream_url` or `music_tracks` — this structural absence is what upholds Constitution Principle III for all 9 reference sources (FR-011, FR-012)
- [ ] T008 Add an `exclude_ids: set[str] | None = None` parameter to `get_sources_for_category` in `apps/api/sources/__init__.py`, defaulting to empty so every existing caller is unaffected
- [ ] T009 [P] Reconcile the two pre-existing registry entries in `apps/api/sources/__init__.py` rather than duplicating them (FR-024): merge `nex1music_ir` into the existing `nex1music` entry as an additional element of `base_urls` keeping `.com` first, and update the existing `radiojavan` entry in place with its confirmed domain and real status
- [ ] T010 Add the 20 new `SourceConfig` entries to `DEFAULT_CONFIGS` in `apps/api/sources/__init__.py`, each setting `kind` explicitly — 11 `full` (`radiojavan`, `musicdel`, `nex1music_ir`, `musicfa`, `upsong`, `upmusics`, `musictarin`, `tehranmusic`, `melodify`, `takmusics`, `one_rj`) and 9 `reference` (`shenoto`, `farsichart`, `aparat`, `namasha`, `rubika`, `fam`, `soundcloud`, `spotify`, `youtube_music`)
- [ ] T011 [P] Add a module-level `INACTIVE_REASONS: dict[str, str]` mapping in `apps/api/sources/__init__.py` giving every disabled source a specific reason naming the actual cause — changed domain, dead domain, requires account, licensed service, video platform, or gated access. A generic "unavailable" is non-conforming (contract G3)
- [ ] T012 Add `source_kind` to the serialized item output in `apps/api/web/app.py`, populated from the owning source's `SourceConfig.kind`, defaulting to `"full"` when the source is unknown
- [ ] T013 Add `kind`, `status`, `inactive_reason`, and `consecutive_failures` to the `/api/sources` response in `apps/api/web/app.py`, deriving status per the data model — `inactive` when `enabled` is false, `degraded` when `consecutive_failures >= 3`, else `active`

**Checkpoint**: Foundation ready — user story implementation can begin in parallel.

---

## Phase 3: User Story 1 - Finding a Persian song across many sources at once (Priority: P1) 🎯 MVP

**Goal**: A search queries every enabled music source, merges results, orders full-source results ahead of reference-source results, and survives any single source failing.

**Independent Test**: Search a well-known Persian track and confirm results from at least 6 distinct music sources appear in one response, correctly ordered, with a failing source not blocking the rest.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T014 [P] [US1] Ordering test in `apps/api/tests/test_source_kind.py`: build a mixed list of full and reference `MediaItem`s, run the ordering helper, assert every `full` item precedes every `reference` item AND that intra-group order is unchanged (FR-005a)
- [ ] T015 [P] [US1] Normalization test in `apps/api/tests/test_api_search.py`: assert an Arabic-script query with Arabic-Indic digits (ي, ٣) returns the same result count as its Persian-script equivalent (ې, 3) (FR-006)
- [ ] T016 [P] [US1] Resilience test in `apps/api/tests/test_api_search.py`: with respx mocking one source to raise and another to succeed, assert the response contains the succeeding source's items plus a `warnings` entry naming the failed one (FR-007, SC-005)

### Implementation for User Story 1

- [ ] T017 [US1] Add a stable ordering helper in `apps/api/web/app.py` placing full-source items before reference-source items, with a key constant within each kind so the pre-existing relevance order is preserved exactly
- [ ] T018 [US1] Apply the ordering in `_collect_items` in `apps/api/web/app.py` after the `asyncio.gather` completes and **before** the `GLOBAL_CACHE.set` call, so cached and fresh responses are identically ordered
- [ ] T019 [US1] Exclude degraded sources from `get_sources_for_category` in `apps/api/web/app.py` when `consecutive_failures >= 3` (FR-018a)
- [ ] T020 [US1] Record search outcomes in `_collect_items` in `apps/api/web/app.py` — call `record_search_failure` once per completed search for each source that failed or returned nothing, and `record_search_success` for each that returned items. The counter MUST move once per search, not once per HTTP request (FR-018a)

**Checkpoint**: User Story 1 fully functional — search returns merged, ordered, failure-tolerant results.

---

## Phase 4: User Story 2 - Playing and downloading a track from a full source (Priority: P2)

**Goal**: Each of the 11 full-source plugins resolves a track to a playable stream and labelled download options, verified offline against captured fixtures.

**Independent Test**: Open a result from one new full source and confirm a playable link and at least one labelled download variant are produced from a captured fixture.

### Tests for User Story 2 ⚠️

- [ ] T021 [P] [US2] Parser tests for all 11 full sources in `apps/api/tests/test_music_scrapers.py`, each following the existing `test_nex1music_item_stream_and_downloads` shape: assert a non-null `stream_url`, at least one `MusicDownloadVariant` with a correct bitrate label, and that every emitted URL passes `is_ad_or_shortener_url` (FR-014)
- [ ] T022 [P] [US2] Add fixture accessor functions to `apps/api/tests/conftest.py` for each new fixture pair, following the existing `nex1music_search_html` pattern exactly — no new fixture infrastructure

### Implementation for User Story 2

Implement one plugin per source, each a standalone module under `apps/api/sources/music/` importing only `sources.base` helpers and never a sibling scraper (Constitution Principle I). Every plugin must catch exceptions and return `[]` rather than propagating (FR-020).

- [ ] T023 [P] [US2] Create `MusicdelPlugin` in `apps/api/sources/music/musicdel.py` with search-result and item-page parsers resolving 320/128/64 kbps variants
- [ ] T024 [P] [US2] Create `MusicFaPlugin` in `apps/api/sources/music/musicfa.py`
- [ ] T025 [P] [US2] Create `UpSongPlugin` in `apps/api/sources/music/upsong.py`
- [ ] T026 [P] [US2] Create `UpMusicsPlugin` in `apps/api/sources/music/upmusics.py`
- [ ] T027 [P] [US2] Create `MusicTarinPlugin` in `apps/api/sources/music/musictarin.py`
- [ ] T028 [P] [US2] Create `TehranMusicPlugin` in `apps/api/sources/music/tehranmusic.py`
- [ ] T029 [P] [US2] Create `MelodifyPlugin` in `apps/api/sources/music/melodify.py`
- [ ] T030 [P] [US2] Create `TakMusicsPlugin` in `apps/api/sources/music/takmusics.py`
- [ ] T031 [P] [US2] Create `OneRJPlugin` in `apps/api/sources/music/one_rj.py` — note it is a related property of Nex1Music but a separate registry entry so one failure does not disable both
- [ ] T032 [P] [US2] Create `RadioJavanPlugin` in `apps/api/sources/music/radiojavan.py` — resolve its true status first; if it is subscription-gated, record it inactive with that reason and skip the plugin (FR-026)
- [ ] T033 [US2] Register all 11 plugins in the factory in `apps/api/sources/__init__.py`, and mark each enabled or disabled according to the status confirmed during capture — a source that could not be verified is recorded disabled with a reason rather than shipped half-working (SC-007)

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Reaching tracks the platform cannot play (Priority: P3)

**Goal**: The 9 reference sources are indexed and surfaced as link-outs with no player, no download control, and no credentials — plus the per-user source-hiding filter.

**Independent Test**: Search for a track present on a reference-only site and confirm it appears in results, is marked as a link-out, leads to the correct page, and shows no media controls.

### Tests for User Story 3 ⚠️

- [ ] T034 [P] [US3] Structural invariant test in `apps/api/tests/test_reference_sources.py`: for every one of the 9 reference plugins, assert `extract_links` returns the item with `stream_url is None` and `music_tracks == []`. This MUST be asserted per subclass, not only on the base class, so a subclass that overrides `extract_links` is caught (FR-011)
- [ ] T035 [P] [US3] Test in `apps/api/tests/test_reference_sources.py` asserting no reference plugin accepts, stores, or forwards any credential, token, or account identifier (FR-012)
- [ ] T036 [P] [US3] Filter tests in `apps/api/tests/test_source_kind.py`: assert a `sources=` exclusion removes that source's results; assert an unknown id is ignored rather than rejected; assert the filtered set is NOT written to `GLOBAL_CACHE` (FR-029, FR-030, FR-031)

### Implementation for User Story 3

- [ ] T037 [US3] Add a repeated `sources` query parameter to `/search` and `/api/search` in `apps/api/web/app.py`, consumed in `_collect_items` **before** `get_sources_for_category` is called so a hidden source is never queried
- [ ] T038 [US3] Apply `exclude_ids` in `_collect_items` in `apps/api/web/app.py`, and add a code comment recording that the filtered result set must never reach `GLOBAL_CACHE.set` — caching it would leak one user's filter into another user's response
- [ ] T039 [P] [US3] Create `ShenotoPlugin` in `apps/api/sources/music/shenoto.py` as a `ReferenceSourcePlugin` subclass
- [ ] T040 [P] [US3] Create `FarsiChartPlugin` in `apps/api/sources/music/farsichart.py` as a `ReferenceSourcePlugin` subclass
- [ ] T041 [P] [US3] Create `AparatPlugin` in `apps/api/sources/music/aparat.py` as a `ReferenceSourcePlugin` subclass
- [ ] T042 [P] [US3] Create `NamashaPlugin` in `apps/api/sources/music/namasha.py` as a `ReferenceSourcePlugin` subclass
- [ ] T043 [P] [US3] Create `RubikaPlugin` in `apps/api/sources/music/rubika.py` as a `ReferenceSourcePlugin` subclass
- [ ] T044 [P] [US3] Create `FamPlugin` in `apps/api/sources/music/fam.py` as a `ReferenceSourcePlugin` subclass
- [ ] T045 [P] [US3] Create `SoundcloudPlugin` in `apps/api/sources/music/soundcloud.py` as a `ReferenceSourcePlugin` subclass
- [ ] T046 [P] [US3] Create `SpotifyPlugin` in `apps/api/sources/music/spotify.py` as a `ReferenceSourcePlugin` subclass
- [ ] T047 [P] [US3] Create `YoutubeMusicPlugin` in `apps/api/sources/music/youtube_music.py` as a `ReferenceSourcePlugin` subclass
- [ ] T048 [P] [US3] Register all 9 reference plugins in the factory in `apps/api/sources/__init__.py` with `kind=SourceKind.REFERENCE`
- [ ] T049 [US3] Render a link-out card in `apps/api/web/templates/_music_card.html` for items with no media: show the outbound link to `page_url` and MUST NOT emit an `<audio>` element or any download control. The element MUST be absent from the DOM — CSS hiding does not satisfy this (SC-003)
- [ ] T050 [P] [US3] Reword the existing "no direct download link found" message in `apps/api/web/templates/_music_card.html` so a reference result reads as a deliberate link-out rather than a failure
- [ ] T051 [P] [US3] Add a reference branch to `apps/web/src/components/cards/MusicCard.tsx` rendering the outbound link with no player and no download controls
- [ ] T052 [P] [US3] Send the saved hidden set as repeated `sources` params in `apps/web/src/lib/api.ts`
- [ ] T053 [US3] Add per-source hide toggles to `apps/web/src/components/InViewFilterBar.tsx`, persisting to `localStorage`, with a control to restore all defaults. A hidden source MUST remain listed with its status so the user can see and undo it; a system-determined `degraded` or `inactive` source MUST NOT be hideable (FR-031)

**Checkpoint**: All reference sources surface as link-outs; the per-user filter works.

> **Note**: The per-user filter tasks (T037, T038, T052, T053) are labelled `[US3]` because the spec places those acceptance scenarios in User Story 3. They serve a different concern from that story's goal and do not depend on the reference-source plugins (T039–T048), so they may be implemented in parallel with them or with User Story 1.

---

## Phase 6: User Story 4 - Every named site has a visible, honest status (Priority: P4)

**Goal**: All 20 named sites appear in the source list with kind, status, and a specific reason whenever not active, and the degraded state is observable.

**Independent Test**: Review the source list and confirm all 20 names appear, each with a kind and active status, and every inactive entry carrying a specific stated reason.

### Tests for User Story 4 ⚠️

- [ ] T054 [P] [US4] Threshold test in `apps/api/tests/test_source_kind.py`: assert 1 and 2 consecutive failures leave a source `active` and still queried, the 3rd marks it `degraded` and excludes it, and any success resets the counter to 0 (FR-018a, SC-009)
- [ ] T055 [P] [US4] Registry completeness test in `apps/api/tests/test_sources_config.py`: assert all 20 named sites are present exactly once, that 11 are `full` and 9 are `reference`, and that every non-active entry has a non-empty specific reason (FR-017, SC-007)
- [ ] T056 [P] [US4] Assert in `apps/api/tests/test_sources_config.py` that `nex1music` and `radiojavan` each appear exactly once, not duplicated (FR-024)

### Implementation for User Story 4

- [ ] T057 [US4] Show kind and status per source in `apps/api/web/templates/base.html`, with the reason displayed whenever status is not `active`
- [ ] T058 [P] [US4] Add a kind badge, status, and reason rendering to `apps/web/src/components/SourceStatusBar.tsx` — kind and status MUST be conveyed by text, not colour alone
- [ ] T059 [US4] Verify both frontends make status and kind accessible: hide toggles are real labelled form controls, keyboard-reachable, with focus order following visual order (contract accessibility section)

**Checkpoint**: Every named site is visibly accounted for.

---

## Phase 7: User Story 5 - Verification without network access (Priority: P5)

**Goal**: The complete suite — including all 20 new sources — passes with no network access, and each new source is verifiable from a committed fixture.

**Independent Test**: Run the full offline suite with the network unavailable and confirm every music source passes.

### Tests for User Story 5 ⚠️

- [ ] T060 [P] [US5] Confirm every registered music source has either a committed fixture and parser test, or a recorded inactive status with a reason — assert this in `apps/api/tests/test_sources_config.py` so the suite fails if a source ships with neither (FR-019, SC-004)
- [ ] T061 [P] [US5] Parked-page and error-page tests in `apps/api/tests/test_music_scrapers.py`: assert each source yields zero results, not junk entries, when fed a domain-parking page, an advertisement, or an error page (FR-020)
- [ ] T062 [P] [US5] Timeout test in `apps/api/tests/test_source_kind.py`: assert a source exceeding its 7s budget is abandoned without blocking the overall search (FR-008)

### Implementation for User Story 5

- [ ] T063 [US5] Run the complete offline suite and confirm 100% of new sources pass with the network unavailable: `cd apps/api && poe test-offline` (SC-004)
- [ ] T064 [US5] Re-run the pre-existing movies and games tests and confirm they pass unchanged from the T001 baseline (SC-010, FR-028)

**Checkpoint**: All five user stories verified offline.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T065 [P] Run lint and type checks: `cd apps/api && poe lint` and `cd apps/web && pnpm check`
- [ ] T066 [P] Trim oversized fixtures in `apps/api/tests/fixtures/` to a representative slice, re-running `poe test-offline` afterwards to confirm the trimmed fixtures still cover every selector the parsers rely on
- [ ] T067 Verify search performance meets the 3-second complete-result-set target in `specs/006-music-sources-expansion/quickstart.md` step 5, with all 20 sources responding normally (SC-006)
- [ ] T068 [P] Confirm in the browser devtools network panel that every media request goes directly to the upstream host and none passes through `localhost:8000` (FR-013, SC-008) — this is the definitive check for Constitution Principle III
- [ ] T069 Run the remaining validation scenarios in `specs/006-music-sources-expansion/quickstart.md` (steps 3, 6, 7, 8, 9, 10) and record the results
- [ ] T070 [P] Update `specs/006-music-sources-expansion/checklists/requirements.md` notes with the final verified status of each of the 20 sites, including any whose confirmed status differs from the spec's initial full/reference assumption (FR-021)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phases 3–7)**: All depend on Foundational completion
  - User stories can then proceed in parallel
  - Or sequentially in priority order (P1 → P2 → P3 → P4 → P5)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: After Foundational — no dependencies on other stories
- **User Story 2 (P2)**: After Foundational — independent of US1
- **User Story 3 (P3)**: After Foundational — independent of US1/US2; its filter tasks are independent of its own reference plugins
- **User Story 4 (P4)**: After Foundational — independent; reads state US1 writes but does not require it
- **User Story 5 (P5)**: After all preceding stories — it verifies them

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T002, T003 (Setup); T004, T005, T006, T011 (Foundational, distinct files)
- T014, T015, T016 (US1 tests); T021, T022 (US2 tests)
- T023–T032 (US2 plugins — 10 tasks, all distinct new files)
- T034, T035, T036 (US3 tests); T039–T047 (US3 reference plugins — 9 tasks, all distinct new files)
- T050, T051, T052, T053 (US3 frontend, distinct files)
- T054, T055, T056 (US4 tests); T058, T060, T061, T062 (distinct files)

**Serialization conflicts** — these touch the same file and must NOT run in parallel:

- `apps/api/sources/__init__.py`: T008 → T009 → T010 → T033 → T048
- `apps/api/web/app.py`: T012, T013 → T017–T020 → T037, T038
- `apps/api/tests/test_source_kind.py`: T014 → T036 → T054 → T062
- `apps/api/tests/test_sources_config.py`: T055 → T056 → T060

---

## Parallel Example: User Story 2

```bash
# All 11 full-source plugins can be written simultaneously — distinct new files,
# no shared imports (Constitution Principle I):
Task: "Create MusicdelPlugin in apps/api/sources/music/musicdel.py"
Task: "Create MusicFaPlugin in apps/api/sources/music/musicfa.py"
Task: "Create UpSongPlugin in apps/api/sources/music/upsong.py"
# ... and so on through one_rj.py and radiojavan.py
```

---

## Parallel Example: User Story 3

```bash
# All 9 reference plugins are small subclasses of the one base class from T007:
Task: "Create SpotifyPlugin in apps/api/sources/music/spotify.py"
Task: "Create SoundcloudPlugin in apps/api/sources/music/soundcloud.py"
Task: "Create AparatPlugin in apps/api/sources/music/aparat.py"
# ... and so on through youtube_music.py

# Simultaneously, the two frontends render the link-out card:
Task: "Render a link-out card in apps/api/web/templates/_music_card.html"
Task: "Add a reference branch to apps/web/src/components/cards/MusicCard.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational — CRITICAL, blocks all stories
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: test US1 independently
5. Deploy/demo if ready

Note that the MVP delivers search across all 20 sources but with reference sources registered and no plugins yet, so ordering is correct but reference results are empty until US3 lands. This is a deliberate, working increment — not a broken one.

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 → Test independently → Deploy (search + ordering + failure tolerance)
3. US2 → Test independently → Deploy (playable full sources)
4. US3 → Test independently → Deploy (reference link-outs + per-user filter)
5. US4 → Test independently → Deploy (status visibility)
6. US5 → Verify the whole thing offline

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US2 (the 11 full-source plugins)
   - Developer B: US3 (the 9 reference plugins)
   - Developer C: US1 + US4
3. Stories integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
- **Constraint that must not be relaxed**: a source that cannot be verified or reached is registered with a real status and a specific reason rather than dropped or shipped half-working. SC-007 is satisfiable honestly this way — an unreachable site recorded as inactive still counts as accounted for
