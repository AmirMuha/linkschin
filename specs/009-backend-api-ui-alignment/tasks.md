# Tasks: Backend API and UI Alignment & Gap Resolution

**Input**: Design documents from `/specs/009-backend-api-ui-alignment/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`  
**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5, US6, US7)
- Exact file paths included in every task description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependency installation and shared environment configuration

- [X] T001 Update `apps/api/pyproject.toml` to add `langchain-core>=0.3.0`, `langchain-openai>=0.2.0`, `pyjwt>=2.8.0`, `passlib[argon2]>=1.7.4`, and `yt-dlp>=2024.0.0` dependencies
- [X] T002 Synchronize Python virtual environment and lockfile by executing `cd apps/api && uv sync --all-extras`
- [X] T003 [P] Create and configure environment templates in `apps/api/.env.example` (`LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`, `JWT_SECRET_KEY`, `OPERATOR_USERNAME`, `OPERATOR_PASSWORD_HASH`) and `apps/web/.env.example` (`NEXT_PUBLIC_API_BASE`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Configure SQLite WAL mode (`PRAGMA journal_mode = WAL;`), foreign keys (`PRAGMA foreign_keys = ON;`), and busy timeout (`PRAGMA busy_timeout = 10000;`) in `apps/api/db.py`
- [X] T005 [P] Implement extended database schema in `apps/api/db.py` creating tables `source_configs`, `source_suggestions`, `conversion_jobs`, `extraction_dead_letter`, and `operator_users` per `data-model.md`
- [X] T006 [P] Implement domain entity dataclasses and Pydantic validation schemas in `apps/api/models.py` per `data-model.md`
- [X] T007 [P] Implement JWT Bearer token creation, validation, password hashing, and FastAPI dependency `get_current_operator` in `apps/api/web/auth.py`
- [X] T008 Implement operator login route `POST /api/auth/login` returning `{ access_token, token_type: "bearer", expires_in }` in `apps/api/web/app.py`

**Checkpoint**: Foundation ready — database WAL mode active, auth framework ready, base models defined.

---

## Phase 3: User Story 1 - Instant Search with Persistent Indexing & On-Demand Fallback (Priority: P1) 🎯 MVP

**Goal**: Deliver sub-50ms repeat search via persistent SQLite FTS5 indexing, dynamic home shelves, and on-demand live scraper fallback for movies.

**Independent Test**: Search for a movie not in the database to trigger live on-demand scraper execution and verify indexing; repeat the query to confirm sub-50ms local database resolution; verify trending/latest home shelves populate from live records.

### Tests for User Story 1

- [X] T009 [P] [US1] Create integration test `apps/api/tests/test_search_indexing.py` verifying that initial live movie search persists items to SQLite and repeat search resolves from FTS5 with `is_cached=True` in <50ms
- [X] T010 [P] [US1] Create contract test `apps/api/tests/test_catalog_api.py` validating responses from `/api/catalog/trending`, `/api/catalog/latest`, and `/api/items/{id}` per `contracts/search-api.yaml`

### Implementation for User Story 1

- [X] T011 [P] [US1] Implement SQLite FTS5 query search with category, quality, censorship, and access-tier filtering in `apps/api/db.py`
- [X] T012 [P] [US1] Implement catalog feed queries `get_trending_items()` and `get_latest_items()` in `apps/api/web/catalog.py`
- [X] T013 [US1] Implement endpoints `GET /api/catalog/trending`, `GET /api/catalog/latest`, and `GET /api/items/{id}` in `apps/api/web/app.py`
- [X] T014 [US1] Refactor `GET /api/search` in `apps/api/web/app.py` to implement the offline-first strategy: query local index first, trigger live on-demand scrape for movies ONLY on DB miss (or `refresh=true`), and serve games/music strictly offline
- [X] T015 [P] [US1] Extend API client methods `fetchTrending()`, `fetchLatest()`, and `fetchItemDetail()` in `apps/web/src/lib/api.ts`
- [X] T016 [US1] Update `apps/web/src/app/page.tsx` and `apps/web/src/components/StaticSections.tsx` to load live trending and latest items from API instead of static `catalog.ts` mock data

**Checkpoint**: User Story 1 functional and independently testable as an MVP increment.

---

## Phase 4: User Story 2 - AI-Assisted Continuous Background Scraping with LangChain (Priority: P2)

**Goal**: Run three independent category background crawlers using LangChain structured extraction to continuously index releases and links into the database.

**Independent Test**: Run a category crawler daemon against sample HTML fixtures and verify LangChain extracts typed Pydantic models with download links, archive passwords, and quality labels into SQLite.

### Tests for User Story 2

- [X] T017 [P] [US2] Create unit test `apps/api/tests/test_extraction_chains.py` validating LangChain structured extraction against raw HTML fixtures for movies, games, and music
- [X] T018 [P] [US2] Create integration test `apps/api/tests/test_worker_daemons.py` verifying background crawler iteration, crawl_state updates, and dead-letter routing on failure

### Implementation for User Story 2

- [X] T019 [P] [US2] Implement HTML pruning via `selectolax` (stripping scripts, styles, navs, footers) and LangChain Pydantic extraction chains (`with_structured_output`) in `apps/api/extraction/chains.py`
- [X] T020 [P] [US2] Implement dead-letter queue persistence `record_dead_letter()` in `apps/api/extraction/dead_letter.py` saving failed raw HTML and error diagnostics to `extraction_dead_letter`
- [X] T021 [US2] Refactor `apps/api/worker.py` to support continuous category daemon execution (`--category movies|games|music|all`) with configurable crawl intervals and error backoff
- [X] T022 [US2] Integrate LangChain structured extraction into `apps/api/worker.py` crawl pipelines for parsing complex download grids and multi-part game archives

**Checkpoint**: User Stories 1 AND 2 functional; database continuously populated by autonomous crawlers.

---

## Phase 5: User Story 3 - Source Registry Management & Community Submissions (Priority: P3)

**Goal**: Provide authenticated source mirror/address configuration, persistent enabled/disabled toggles, and community portal suggestion review queue.

**Independent Test**: Authenticate as operator, modify a source base URL and toggle status, verify persistence across server restarts, and submit a suggestion through the UI form to confirm queue recording.

### Tests for User Story 3

- [X] T023 [P] [US3] Create integration test `apps/api/tests/test_sources_management.py` testing `PATCH /api/sources/{id}` (auth required), `POST /api/sources/suggest`, and suggestion deduplication
- [X] T024 [P] [US3] Create contract test `apps/api/tests/test_sources_contracts.py` validating responses against `contracts/sources-api.yaml`

### Implementation for User Story 3

- [X] T025 [P] [US3] Implement SQLite persistence for `source_configs` (overrides) and `source_suggestions` (deduplication by domain, vote count increment) in `apps/api/db.py`
- [X] T026 [US3] Implement endpoints `PATCH /api/sources/{id}`, `PATCH /api/sources/{id}/toggle`, `POST /api/sources/suggest`, and `GET /api/admin/suggestions` in `apps/api/web/app.py`
- [X] T027 [P] [US3] Update `apps/web/src/lib/api.ts` adding `updateSourceAddress()`, `toggleSourceEnabled()`, and `submitSourceSuggestion()`
- [X] T028 [US3] Connect `apps/web/src/app/sources/page.tsx` to live `GET /api/sources`, `PATCH /api/sources/{id}`, and `POST /api/sources/suggest` endpoints

**Checkpoint**: User Stories 1, 2, and 3 functional; operator console connected to live database.

---

## Phase 6: User Story 4 - Authentic YouTube to MP3 Audio Extraction (Priority: P4)

**Goal**: Provide authentic YouTube music video audio extraction with real-time status polling and immediate binary streaming with zero persistent server storage.

**Independent Test**: Submit a valid public YouTube link, monitor status transitions (queued → processing → completed), download the resulting MP3 attachment, and verify immediate deletion of temporary audio files.

### Tests for User Story 4

- [X] T029 [P] [US4] Create unit test `apps/api/tests/test_convert_worker.py` validating `yt-dlp` extraction parameters, rate limiting (20/hr/IP), and cleanup hooks
- [X] T030 [P] [US4] Create contract test `apps/api/tests/test_convert_api.py` validating endpoints against `contracts/youtube-mp3-api.yaml`

### Implementation for User Story 4

- [X] T031 [P] [US4] Implement asynchronous audio extraction worker using `yt-dlp` and `ffmpeg` in `apps/api/web/convert.py` with job tracking and temporary directory allocation (`/tmp/linkschin_mp3/{job_id}/`)
- [X] T032 [US4] Implement `POST /api/convert`, `GET /api/convert/{id}`, and `GET /api/convert/history` in `apps/api/web/app.py`
- [X] T033 [US4] Implement `GET /api/download/{id}` in `apps/api/web/app.py` returning `FileResponse` with background task hook that immediately deletes the temporary MP3 file and folder upon stream close
- [X] T034 [P] [US4] Update `apps/web/src/lib/api.ts` adding `startConversion()`, `pollConversion()`, and `getConversionHistory()`
- [X] T035 [US4] Connect `apps/web/src/app/youtube-to-mp3/page.tsx` to live convert, status polling, and stream download APIs

**Checkpoint**: User Stories 1 through 4 functional; authentic MP3 extraction running with zero media retention.

---

## Phase 7: User Story 5 - Intelligent Context-Aware Search Assistant (Priority: P5)

**Goal**: Deliver a natural-language search assistant powered by a LangChain agent with function tools over the media catalog and source health records.

**Independent Test**: Inquire about dubbed 1080p releases or offline sources in Persian/English and verify that the response cites verified database entities with interactive media cards.

### Tests for User Story 5

- [X] T036 [P] [US5] Create unit test `apps/api/tests/test_chat_agent.py` verifying LangChain tool-calling execution against catalog search and source health queries
- [X] T037 [P] [US5] Create contract test `apps/api/tests/test_chat_contracts.py` validating `POST /api/chat` against `contracts/chat-api.yaml`

### Implementation for User Story 5

- [X] T038 [P] [US5] Implement LangChain tools `search_catalog`, `check_source_health`, and `inspect_game_archive` in `apps/api/web/chat.py`
- [X] T039 [US5] Implement conversational agent loop and SSE stream generator emitting `status`, `delta`, and `media_card` events in `apps/api/web/chat.py`
- [X] T040 [US5] Register `POST /api/chat` and `DELETE /api/chat/session/{id}` in `apps/api/web/app.py`
- [X] T041 [US5] Connect `apps/web/src/components/AiAssistant.tsx` to `POST /api/chat` supporting SSE streaming and dynamic media card display

**Checkpoint**: All 5 user stories functional and integrated across backend and frontend.

---

## Phase 8: User Story 6 - Centralized Adaptive Background Scraping Pipeline (Priority: P2)

**Goal**: Coordinate continuous crawling across media categories through a centralized adaptive priority queue with domain concurrency limits and exponential backoff on throttling.

**Independent Test**: Enqueue high-priority live search queries and background crawl tasks concurrently; verify that live queries preempt background tasks, per-domain concurrency limits prevent flooding, and 429 errors trigger isolated exponential backoff without stalling other domains.

### Tests for User Story 6

- [X] T042 [P] [US6] Create unit test `apps/api/tests/test_crawler_queue.py` validating priority preemption (P0 user search > P1 background crawl), domain concurrency limits, and adaptive backoff calculation
- [X] T043 [P] [US6] Create integration test `apps/api/tests/test_adaptive_throttle.py` verifying domain-level backoff on simulated 429/timeout responses while concurrent domain scrapers proceed unhindered

### Implementation for User Story 6

- [X] T044 [P] [US6] Implement `DomainThrottlePolicy` in `apps/api/crawler/throttle.py` managing per-domain concurrency semaphores, request rate-limits, and exponential backoff state with jitter
- [X] T045 [P] [US6] Implement `AdaptiveCrawlQueue` in `apps/api/crawler/queue.py` with priority levels (P0 live search, P1 scheduled crawl) and domain dispatch loop
- [X] T046 [US6] Integrate `AdaptiveCrawlQueue` into `apps/api/web/app.py` for on-demand search dispatch and `apps/api/worker.py` for continuous background scheduling

**Checkpoint**: Centralized adaptive queue managing all scraper jobs with priority scheduling and anti-ban domain isolation.

---

## Phase 9: User Story 7 - Strict AI-Assisted Structured Extraction and DLQ Reliability (Priority: P3)

**Goal**: Guarantee zero dropped listings and strict data integrity via Pydantic schema validation, dead-letter queue (DLQ) capture of failed extractions, and automated retry re-processing.

**Independent Test**: Process unparseable HTML and simulated LLM timeouts through the extraction pipeline; verify that raw payloads are captured in `extraction_dead_letter` as `pending`; trigger the DLQ retry task and verify clean database upsert without duplicate records.

### Tests for User Story 7

- [X] T047 [P] [US7] Create unit test `apps/api/tests/test_dlq_pipeline.py` testing DLQ error recording, retry scheduling, and state transitions (`pending` → `resolved` / `failed`)
- [X] T048 [P] [US7] Create contract test `apps/api/tests/test_dlq_api.py` validating `GET /api/admin/dlq` and `POST /api/admin/dlq/{id}/retry` against `contracts/dlq-api.yaml`

### Implementation for User Story 7

- [X] T049 [P] [US7] Implement `extraction_dead_letter` CRUD operations and retry re-processor in `apps/api/extraction/dead_letter.py` with backoff scheduling and duplicate prevention
- [X] T050 [US7] Implement administrative endpoints `GET /api/admin/dlq` and `POST /api/admin/dlq/{id}/retry` (Operator Auth) in `apps/api/web/app.py`
- [X] T051 [US7] Wire the background DLQ retry task into the daemon worker in `apps/api/worker.py` to periodically re-process eligible pending items

**Checkpoint**: Strict schema enforcement and resilient dead-letter queue recovery active across all ingestion pipelines.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, code quality, and end-to-end quickstart validation

- [X] T052 [P] Update `README.md` and `apps/api/README.md` documenting environment configuration, worker daemon startup commands, queue architecture, and API endpoints
- [X] T053 Run backend linting and compilation check via `cd apps/api && uv run poe lint`
- [X] T054 Run frontend TypeScript check via `cd apps/web && pnpm check`
- [X] T055 Execute all validation scenarios in `specs/009-backend-api-ui-alignment/quickstart.md` (Scenarios 1-8) and verify clean end-to-end execution
