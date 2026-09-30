---

description: "Task list for movie source expansion (20 requested sites)"
---

# Tasks: Movie Source Expansion (20 Requested Sites)

**Input**: Design documents from `/specs/005-movie-source-expansion/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-contract.md, quickstart.md

**Tests**: Included. FR-025 and SC-010 mandate offline fixture verification for every new source, so test tasks are required rather than optional.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Paths

Backend: `apps/api/` · Web client: `apps/web/src/` · All backend paths relative to `apps/api/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Configuration layer the new sources register through

- [ ] T001  Create `apps/api/sources/profiles.yaml` declaring all 20 requested sites with `id`, `name`, `category: movies`, `provides_downloads`, `parser`, and `addresses` (FR-001, FR-003) — using the observed-reachable addresses from research.md R-001 (filmnet.ir, gapfilm.ir, telewebion.ir, danfilo.ir, sarvnema.ir, namasha.com), NOT the commonly-known names
- [ ] T002  Create `apps/api/sources/profiles.py` with a `SourceProfile` dataclass and `load_profiles(path)` that reads the YAML at startup and returns profiles merged into the source registry
- [ ] T003 [P] Add `provides_downloads: bool = True`, `inactive_reason: str | None = None`, and `last_reachable_at: str | None = None` fields to `SourceConfig` in `apps/api/models.py`, keeping `primary_base_url` unchanged (FR-003)
- [ ] T004 **DONE — no action.** PyYAML 6.0.3 is already installed in `apps/api/.venv`, so `sources/profiles.yaml` needs no dependency change. Verified: `python -c "import yaml"` succeeds. Do not add a dependency to `pyproject.toml`.

**Checkpoint**: profiles load without error and the registry reports 20 movie sources

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005  Add `watch_url: str | None = None` to `MediaItem` in `apps/api/models.py`, and validate it in `__post_init__` with the existing `validate_media_url` — absolute `http`/`https` with a netloc only. It MUST remain a **separate concept from `stream_url`** (a playable direct file) and MUST NOT reuse that column
- [ ] T006  Create `apps/api/sources/health.py` with a `SourceState` enum (`providing_results`, `subscription_only`, `unreachable`, `requires_login`, `not_yet_proven`), a `SourceHealth` dataclass carrying `source_id`, `state`, `reason`, `last_success_at`, `last_failure_at`, `consecutive_failures`, `active_address`, and a module-level registry with `record_success(source_id, address)` (FR-008), `record_failure(source_id, reason)`, `record_empty_response(source_id)`, and `get(source_id)`
- [ ] T007 [P] Add the `source_health` table to `apps/api/db.py` with `get_source_health()` / `set_source_health()` following the existing `get_last_page` / `set_last_page` per-source pattern
- [ ] T008 Persist and restore `watch_url` in `db.upsert_items` and `db._rehydrate` in `apps/api/db.py` — without this, watch-only items lose their destination on the first cache read
- [ ] T009  Implement ordered multi-address iteration in `apps/api/sources/__init__.py`: replace the `primary_base_url`-only read with a loop over `cfg.base_urls`, skipping addresses the circuit breaker has marked dead, and record which address served the request (FR-012, SC-009)
- [ ] T009b  Replace the hardcoded `if/elif cfg.id == ...` dispatch chain in `get_sources_for_category()` with a registry dict mapping source id to plugin class. Today a config with no matching branch is **silently dropped** (no `else: raise`), which is exactly the "registers but returns nothing" failure FR-023 forbids — with 19 new sources the chain is also 19 more branches. A dict deletes branches instead of adding them, and a missing entry can fail loudly (FR-023)
- [ ] T010  Implement the circuit breaker in `apps/api/sources/health.py`: after N consecutive failures on one address, skip it for subsequent requests within a cooldown, so a dead source does not consume its full 7s timeout on every search (protects the 10s global budget at 6x source count)
- [ ] T011  Enforce bounded redirects in `apps/api/http_client.py` — currently `follow_redirects=True` with no cap, and tiwall.com/fam.ir loop indefinitely. Cap the chain and surface a redirect-loop failure reason rather than hanging
- [ ] T012  Validate profile addresses at load in `apps/api/sources/profiles.py`: reject a non-absolute or non-`http`/`https` address with an error naming the source id and the offending value; never silently drop it (FR-014). Reject an unknown `parser` name rather than registering a source that silently returns nothing (FR-023)
- [ ] T013  Wire health recording into `apps/api/web/app.py::_collect_items`: record success on results, failure on exception/timeout, and `record_empty_response` when HTTP 200 yields zero parseable items (FR-019)
- [ ] T013b  Confirm every new source receives the already-normalized query — `normalize_persian_text` is applied once in `apps/api/web/app.py::_collect_items` before plugins are dispatched, so all 19 inherit it. Add a test asserting a new plugin builds its search URL from `query.normalized_query`, proving the constitutional NFKC gate holds for the new sources (FR-027). No production change expected — this is a verification task
- [ ] T014  Extend `/api/sources` in `apps/api/web/app.py` to include `provides_downloads`, `state`, `inactive_reason`, `last_reachable_at`, and `active_address` per source, and extend `/api/health` with `source_health` and `source_health_counts` (FR-008)
- [ ] T015  Add `SourceInfo` and `SourceState` types to `apps/web/src/types/media.ts`, leaving the `Category` union unchanged as `'movies' | 'games' | 'music'`

**Checkpoint**: Foundation ready — a source with multiple addresses uses the fallback, health state round-trips through SQLite, and a dead source fails fast. Verify with `cd apps/api && python -m pytest tests/ -q` (existing suite must still pass — FR-024)

---

## Phase 3: User Story 1 - Finding a Requested Site in Search Results (Priority: P1) 🎯 MVP

**Goal**: All 20 requested sites registered, discoverable, and contributing results where they have public links

**Independent Test**: Search for a well-known Persian film and verify results are attributed to requested sites, and that all 20 appear in `/api/sources` each with a state and, when inactive, a reason

### Tests for User Story 1

> Write first, confirm they FAIL before implementing

- [ ] T016 [P] [US1] Registry test in `apps/api/tests/test_sources_config.py` asserting all 20 requested ids are present and UpTV resolves to the existing entry with no duplicate (FR-001, FR-002)
- [ ] T017 [P] [US1] Offline parser test per new download source in `apps/api/tests/test_movies_scrapers.py`, following the existing `uptvs` / `doostihaa` convention — call `plugin.parse_search_results(fixture_html)` directly. Do **not** use `respx`: it is declared in dev extras but has zero usages in the repo, and movie tests are pure-function fixture parsing
- [ ] T018 [P] [US1] Add per-source fixture accessors to `apps/api/tests/conftest.py` — one `<site>_search_html` and one `<site>_item_html` fixture per new source, matching the existing per-source pattern
- [ ] T018b [P] [US1] Register every new fixture in the offline runner `apps/api/tests/run_all.py` — it does **not** auto-discover tests: it imports each module explicitly and injects fixtures from a hardcoded fix_map, so a fixture present only in `conftest.py` passes under `pytest` but is **never executed** by `python tests/run_all.py`, the constitutional offline gate (Principle IV, FR-025). Add each new fixture to the `tmov` fix_map, and add a `modules` entry if any new test file is created
- [ ] T019 [US1] Contract test in `apps/api/tests/test_api_search.py` asserting `/api/sources` returns every registered source including unreachable ones — absence is never used to represent a dead source (FR-009a)
- [ ] T020 [US1] Deduplication test in `apps/api/tests/test_api_search.py` asserting duplicate entries for the same title from the same source collapse to one (FR-018)

### Implementation for User Story 1

- [ ] T021 [P] [US1] Create `apps/api/sources/movies/babakfilm.py` implementing the `SourcePlugin` protocol — confirmed real search page (345 KB vs 488 KB home), so `?s=` genuinely works. Follow the existing `doostihaa.py` / `uptvs.py` structure exactly: stdlib `re` parsing (**not** selectolax, which is declared in `pyproject.toml` but has zero usages in the repo), a `base_url` property off `config.primary_base_url`, and a pure sync `parse_search_results(html)` that is the unit-test seam
- [ ] T021b [P] [US1] Add a base-url-override test per new plugin, following `test_search_parsers_survive_base_url_override` in `apps/api/tests/test_movies_scrapers.py` — it rewrites the host to `http://127.0.0.1:8899` and asserts the item count is unchanged. **Never hardcode a host in a parser regex**; always resolve through `clean_absolute_url(self.base_url, raw)`, or the parser silently returns zero items under override and the domain-fallback feature (FR-012a) cannot work
- [ ] T022 [P] [US1] Create `apps/api/sources/movies/gapfilm.py` — note `?s=` may soft-404; verify against the captured fixture before relying on it
- [ ] T023 [P] [US1] Create `apps/api/sources/movies/filmchiin.py` — `?s=test` returned 100774 B, byte-identical to the homepage, so do NOT assume `?s=` — capture the site homepage fixture first, read its search form action from the HTML, and build the search URL from what the page actually declares
- [ ] T024 [P] [US1] Create `apps/api/sources/movies/imvbox.py` — `?s=test` 413276 B vs home 413263 B, effectively a soft-404; read the real search route from the captured fixture rather than assuming `?s=`
- [ ] T025 [P] [US1] Create `apps/api/sources/movies/filmtarin.py` — WordPress confirmed
- [ ] T026 [P] [US1] Create `apps/api/sources/movies/sarvnema.py` — WordPress confirmed, address `sarvnema.ir`
- [ ] T027 [P] [US1] Create `apps/api/sources/movies/danfilo.py` — WordPress confirmed, address `danfilo.ir`
- [ ] T028 [P] [US1] Create `apps/api/sources/movies/telewebion.py` — address `telewebion.ir`
- [ ] T029 [P] [US1] Create `apps/api/sources/movies/filmnet.py` — address `filmnet.ir`
- [ ] T030 [P] [US1] Create `apps/api/sources/movies/namasha.py` — address `namasha.com`
- [ ] T031 [P] [US1] Create `apps/api/sources/movies/aparat.py` — video platform, registered under movies per user direction
- [ ] T032 [P] [US1] Create `apps/api/sources/movies/rubika.py` — children's channel registered under movies per user direction; not a download portal, so it must not have download links constructed for it
- [ ] T032b [P] [US1] Create `apps/api/sources/movies/digitoon.py` — children's channel registered under movies per user direction; not a download portal
- [ ] T032c [P] [US1] Create `apps/api/sources/movies/fam.py` — children's channel; note Fam has **no confirmed working address** (308 redirect loop per research.md R-001), so it registers with state `not_yet_proven` and cannot have a fixture-captured parser test until an address is supplied
- [ ] T033 [P] [US1] Create `apps/api/sources/movies/ndamedia.py` — general media outlet registered under movies per user direction
- [ ] T034 [P] [US1] Register all new plugins in `apps/api/sources/movies/__init__.py` and `apps/api/sources/__init__.py`, including the four sites with no confirmed working address (ndamedia, salamscinema, tiwall, fam) which register with state `not_yet_proven`
- [ ] T035 [US1] Enforce the discard rules in `apps/api/web/app.py::_collect_items`: drop any item that has neither a populated `movie_variants` nor a `watch_url` (FR-017, FR-018, SC-001, SC-002)
- [ ] T036 [US1] Render every source in `apps/web/src/components/SourceStatusBar.tsx` including inactive ones, and render `state` and `inactive_reason` per `contracts/api-contract.md`

**Checkpoint**: All 20 sites registered and listed; searches return results attributed to them. Verify with quickstart.md Check 1 and Check 8

---

## Phase 4: User Story 2 - Watching Where a Title Is Available When No Download Exists (Priority: P2)

**Goal**: Subscription services return a legitimate watch destination and never a download

**Independent Test**: Search for a title that exists only on a subscription service and verify the result shows a watch destination with no download button, and that download and watch actions are visually distinct

### Tests for User Story 2

> The FR-006/FR-007 boundary test is the most important in this feature — a failure is a blocking defect, not a bug to work around

- [ ] T037 [P] [US2] Boundary test in `apps/api/tests/test_movies_scrapers.py` asserting every source with `provides_downloads=False` returns items with `watch_url` set and `movie_variants` **empty** (FR-006, SC-007)
- [ ] T038 [P] [US2] Test in `apps/api/tests/test_movies_scrapers.py` asserting no gated title ever produces a populated `movie_variants` (FR-007)
- [ ] T039 [US2] Cache round-trip test in `apps/api/tests/test_db.py` asserting `watch_url` survives `upsert_items` → `search` (FR-005 persistence, R-005)
- [ ] T040 [US2] Test in `apps/api/tests/test_api_search.py` asserting `category` gains no new value and a watch-only item serialises with the expected shape

### Implementation for User Story 2

- [ ] T041 [P] [US2] Create `apps/api/sources/movies/namava.py` — `provides_downloads=False`; returns `watch_url` only
- [ ] T042 [P] [US2] Create `apps/api/sources/movies/filimo.py` — `provides_downloads=False`; returns `watch_url` only
- [ ] T043 [P] [US2] Create `apps/api/sources/movies/salamcinema.py` — `provides_downloads=False`; no confirmed working address yet
- [ ] T044 [P] [US2] Create `apps/api/sources/movies/tiwall.py` — `provides_downloads=False`; redirect loop, needs bounded-redirect handling from T011
- [ ] T045 [US2] Render watch actions in `apps/web/src/components/cards/MovieCard.tsx`: `watch_url` set with empty `movie_variants` renders a watch action and **no download button**; `movie_variants` non-empty renders download actions; the two must be visually distinct (FR-017)
- [ ] T046 [US2] Add the streaming toggle to the Movies category in `apps/web/src/components/SearchBar.tsx` — switches between downloads-only (**default**) and all sources including watch-only. **Do not add a new tab** (FR-005, clarification Q1)
- [ ] T047 [US2] Verify the server never fetches or proxies `watch_url` — it points at the source's own page and is returned as a string only (FR-026, Principle III)

**Checkpoint**: Subscription sources return watch destinations with zero download links. Verify with quickstart.md Check 6

---

## Phase 5: User Story 3 - Recovering When a Source Goes Down or Changes (Priority: P3)

**Goal**: Dead and silently-broken sources degrade visibly without breaking search

**Independent Test**: Simulate a requested source returning errors or timing out and verify search still succeeds using remaining sources, and the failing source is reported as degraded rather than silently dropped

### Tests for User Story 3

- [ ] T048 [P] [US3] Failure-isolation test in `apps/api/tests/test_sources_config.py` asserting a source whose every address errors does not prevent healthy sources returning results within the 10s budget (FR-010, SC-004)
- [ ] T049 [P] [US3] Fallback test asserting a source with a dead primary and live fallback still returns results (FR-012a, SC-009a)
- [ ] T050 [P] [US3] Silent-break test asserting a source returning HTTP 200 with unparseable content increments `consecutive_failures` and is reported degraded, while a source with genuinely no matching titles does not (FR-019)
- [ ] T051 [P] [US3] Breaker test asserting a known-dead address is not re-attempted on every subsequent request (FR-012b)
- [ ] T052 [P] [US3] Auto-recovery test asserting a source returning to `unreachable` automatically returns to active participation on the next success, with no manual intervention (FR-009c, SC-001a)
- [ ] T053 [P] [US3] Ad/parked test asserting results from ad-shortener and parked-domain pages are discarded (FR-016, SC-006)
- [ ] T054 [P] [US3] Redirect-loop test asserting a source in a redirect loop is marked degraded rather than hanging (FR-015, tiwall.com / fam.ir)
- [ ] T055 [US3] Alias test asserting a source marked a duplicate of another does not produce a separate result stream (FR-021)

### Implementation for User Story 3

- [ ] T056 [US3] Surface `last_reachable_at` and the plain-language `inactive_reason` for every non-contributing source in `/api/sources` (FR-009, FR-009b)
- [ ] T057 [US3] Persist health state so `unreachable` → `providing_results` happens automatically on the first success after a failure, with no manual intervention (FR-009c)
- [ ] T058 [US3] Mark `REQUIRES_LOGIN` sticky — a source behind a bot wall is not retried on every search, because the platform does not attempt interactive sign-in (R-007)
- [ ] T059 [US3] Expose the maintainer diagnostic view in `/api/health`: per-source state, `consecutive_failures`, `last_success_at`, and last failure reason, so a maintainer needs no log access (FR-020, SC-011)
- [ ] T060 [US3] Support disabling a source through configuration taking effect on next startup, with its notes retained (FR-013, clarification Q3)
- [ ] T061 [US3] Support marking a source an alias of another so it does not create a duplicate result stream (FR-021)
- [ ] T062 [US3] Verify ad-shortener, referral, and parked-domain filtering still applies to every new source via the existing `is_ad_or_shortener_url` and `is_parked_page` helpers in `apps/api/sources/base.py` (FR-016)

**Checkpoint**: Sources can fail and recover without breaking search. Verify with quickstart.md Check 5 and Check 7

---

## Phase 6: User Story 4 - Adding a Future Site Without Engineering Work (Priority: P4)

**Goal**: A new site is registered by configuration when a parser for its shape already exists

**Independent Test**: Describe an unconfigured site declaratively, enable it, and verify it participates in search using the same result model

### Tests for User Story 4

- [ ] T063 [P] [US4] Profile validation test in `apps/api/tests/test_sources_config.py` asserting an invalid address is rejected with a message naming the source id and value, not silently dropped (FR-014)
- [ ] T064 [P] [US4] Unknown-parser test asserting a profile naming a parser that does not exist is rejected rather than registered as a silent no-op (FR-023)
- [ ] T065 [US4] Config-only registration test asserting a new profile with an existing parser name becomes searchable with no code change (FR-022)

### Implementation for User Story 4

- [ ] T066 [US4] Register parsers by name in `apps/api/sources/profiles.py` so a profile resolves its `parser` to an implementation, allowing several profiles to share one parser
- [ ] T067 [US4] Reject a profile whose `parser` is unknown at load time, reporting the unknown name — never register a source that silently returns nothing (FR-023, SC-003)
- [ ] T068 [US4] Document in `apps/api/sources/profiles.yaml` header comments that adding a site of a new shape requires a dedicated parser, and that only that parser is new code (FR-022, Principle I)
- [ ] T069 [US4] Verify no administrative screen was introduced for adding sources — configuration file only (clarification Q3)

**Checkpoint**: Verify with quickstart.md Check 3

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T070 [P] Confirm no media payload passes through the server for any of the 19 new sources — verify via `apps/api/tests/test_streaming.py` (FR-026, SC-008, Principle III)
- [ ] T071 [P] Confirm zero search requests exceed the 10s global budget with all 23 registered sources, and that per-source timeouts hold at 7s (FR-011, SC-005)
- [ ] T072  Confirm the full existing suite passes unchanged, including current `uptvs`, `doostihaa`, `downloadha`, `yasdl`, `popmusic`, `nex1music` tests (FR-024, SC-012)
- [ ] T073  Record the four sites with no confirmed working address (ndamedia, salamscinema, tiwall, fam) as a documented gap in `specs/005-movie-source-expansion/quickstart.md`, so their missing fixtures are a recorded limitation rather than a silent omission
- [ ] T074 [P] Run the offline runner `python apps/api/tests/run_all.py` and the web client `node --test apps/web/src/lib/*.test.ts`
- [ ] T075 [P] Run `pnpm lint` at the repository root

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational
- **Polish (Phase 7)**: Depends on all desired user stories

### User Story Dependencies

- **User Story 1 (P1)**: After Foundational. No story dependencies. **This is the MVP.**
- **User Story 2 (P2)**: After Foundational. Uses `watch_url` from T005, but independently testable.
- **User Story 3 (P3)**: After Foundational. Uses health registry from T006. Independently testable.
- **User Story 4 (P4)**: After Foundational. Uses profile loader from T002. Independently testable.

### Within Each User Story

- Tests written and FAILING before implementation
- Models before services, services before endpoints
- Story complete before moving to the next priority

### Critical Path

```
T001 → T002 → T005 → T006 → T013 → T016..T020 → T021..T034 → T036
                                    ↑
                        (T021-T033 are the long pole: 19 bespoke parsers)
```

T021–T034 is the bulk of the work and parallelizes across people. Each is independent — separate
files, no cross-dependencies.

### Parallel Opportunities

- T003, T004 parallel (independent files)
- T007, T008 parallel (both `db.py` but distinct functions — coordinate, do not run concurrently)
- T016–T018 parallel; T021–T034 all parallel
- T037–T038 parallel; T041–T044 parallel
- T048–T055 parallel; T063–T064 parallel

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE** — quickstart.md Checks 1, 8, 10
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → validate → deploy (**MVP**: all 20 sites registered and listed)
3. US2 → validate → deploy (subscription sites return watch destinations)
4. US3 → validate → deploy (resilience against churn)
5. US4 → validate → deploy (config-only site addition)

Each story delivers value without breaking the previous ones.

---

## Notes

- **[P]** = different files, no dependencies
- **[Story]** maps each task to a user story for traceability
- Constitution Principle I: every parser in T021–T034 is a standalone module depending on no sibling
  scraper; shared helpers come only from `apps/api/sources/base.py`
- Constitution Principle IV: every source in T021–T034 needs a fixture pair from T018. The four
  sites with no confirmed address cannot have one — that is the recorded gap in T074
- No task adds a dependency. PyYAML (T004) is the only possible addition, and only if absent
- FR-022 was narrowed after live fingerprinting found only 3 of 16 reachable sites run WordPress.
  A general pattern engine was rejected as speculative — see plan.md Complexity Tracking
