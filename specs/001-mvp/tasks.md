---
description: "Task list for Iranian Multi-Media Direct Link Aggregator (MVP) implementation"
---

# Tasks: Iranian Multi-Media Direct Link Aggregator (MVP)

**Input**: Design documents from `/specs/001-mvp/`
**Prerequisites**: `plan.md`, `spec.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md`
**Tests**: Unit & fixture parser tests included per project plan for scraper verification

## Format: `- [ ] [TaskID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (US1, US2, US3, US4, US5)
- Exact file paths referenced to monorepo layout: `apps/api/...`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic directory structure

- [X] T001 Create project package directory structure (`apps/api/`, `apps/api/sources/{movies,games,music}`, `apps/api/web/{static,templates}`, `apps/api/tests/fixtures/`)
- [X] T002 Create `pyproject.toml` with dependencies (`fastapi`, `uvicorn`, `jinja2`, `httpx`, `selectolax`, `cachetools`) and dev dependencies in `apps/api/pyproject.toml`
- [X] T003 [P] Configure test runner and mock HTTP helpers in `apps/api/tests/run_all.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure and base types that MUST be complete before user stories

- [X] T004 Implement domain entities in `apps/api/models.py` (`Category`, `SourceConfig`, `SearchQuery`, `MediaItem`, `MovieDownloadVariant`, `GameRelease`, `GamePartLink`, `MusicTrack`, `MusicDownloadVariant`, `CachedResult`)
- [X] T005 [P] Implement asynchronous HTTP client with custom headers, cookie jar, and redirect handling in `apps/api/http_client.py`
- [X] T006 [P] Implement Persian/Arabic Unicode normalization and TTLCache in `apps/api/cache.py`
- [X] T007 Implement `SourcePlugin` protocol and registry lookup in `apps/api/sources/base.py` and `apps/api/sources/__init__.py`
- [X] T008 Set up FastAPI application, Jinja2 template renderer, and static mount in `apps/api/web/app.py` and `apps/api/web/templates/base.html`
- [X] T009 [P] Implement CLI scraper smoke check runner in `apps/api/cli_check.py`

**Checkpoint**: Foundation ready — user story implementation can begin

---

## Phase 3: User Story 1 - Movies Search & Download Extraction (Priority: P1)

*Status: Honest Empty State. All 4 target movie domains (film2media.click, avasds.ir, zarfilm.click, mobomovie.com) are NXDOMAIN or parked lander pages at DNS level. Registered as disabled in sources config, UI returns clear Persian notice.*

- [ ] T010 [P] [US1] (BLOCKED-UPSTREAM) Create sample HTML search fixtures for movies in `apps/api/tests/fixtures/film2media_search.html` and `apps/api/tests/fixtures/avamovie_search.html`
- [ ] T011 [P] [US1] (BLOCKED-UPSTREAM) Implement Film2Media scraper plugin in `apps/api/sources/movies/film2media.py` (Domain `film2media.click` NXDOMAIN)
- [ ] T012 [P] [US1] (BLOCKED-UPSTREAM) Implement AvaMovie scraper plugin in `apps/api/sources/movies/avamovie.py` (Domain `avasds.ir` NXDOMAIN)
- [ ] T013 [P] [US1] (BLOCKED-UPSTREAM) Implement Zarfilm scraper plugin in `apps/api/sources/movies/zarfilm.py` (Domain `zarfilm.click` NXDOMAIN)
- [ ] T014 [P] [US1] (BLOCKED-UPSTREAM) Implement MoboMovie scraper plugin in `apps/api/sources/movies/mobomovie.py` (Domain `mobomovie.com` parked lander)
- [X] T015 [US1] Implement movie card template in `apps/api/web/templates/_movie_card.html` categorizing resolution, codec, and dub/sub badges
- [X] T016 [US1] Implement movie search endpoint and results rendering in `apps/api/web/app.py` and `apps/api/web/templates/results.html`
- [ ] T017 [P] [US1] (BLOCKED-UPSTREAM) Write unit tests in `apps/api/tests/test_movies_scrapers.py` verifying movie search and format extraction against fixtures

---

## Phase 4: User Story 2 - Complete Multi-Part Game Archive Extraction (Priority: P1) 🎯 MVP

**Goal**: Enable gamers to search games and receive complete, ordered split RAR archive links (Part 1..N) with file sizes, extraction passwords, and a one-click copy button.

**Independent Test**: Run `python apps/api/cli_check.py --category games --source downloadha --query "noire"` and verify parts are sequential with archive password.

- [X] T018 [P] [US2] Create sample HTML search fixtures for games in `apps/api/tests/fixtures/downloadha_search.html` and `apps/api/tests/fixtures/downloadha_item.html`
- [ ] T019 [P] [US2] (BLOCKED-UPSTREAM) Implement YasDL scraper plugin in `apps/api/sources/games/yasdl.py` (Blocked by Google reCAPTCHA)
- [X] T020 [P] [US2] Implement Downloadha scraper plugin in `apps/api/sources/games/downloadha.py` with multi-part parsing, total file size, and password extraction
- [ ] T021 [P] [US2] (BLOCKED-UPSTREAM) Implement Game2DL scraper plugin in `apps/api/sources/games/game2dl.py` (Domain offline / NXDOMAIN)
- [X] T022 [US2] Implement game release card template in `apps/api/web/templates/_game_card.html` displaying ordered parts, total size, password copy button, and "Copy all links" action
- [X] T023 [US2] Integrate game search and card rendering in `apps/api/web/app.py`
- [X] T024 [P] [US2] Write unit tests in `apps/api/tests/test_games_scrapers.py` verifying sequential part ordering, gap detection, total size, and password extraction

**Checkpoint**: User Story 2 fully functional and verified against live sources and offline fixtures.

---

## Phase 5: User Story 3 - Music Track Discovery, Preview, and Download (Priority: P1)

**Goal**: Enable music listeners to search Persian tracks, preview them via an inline HTML5 audio player, and download 128k/320k MP3s directly.

**Independent Test**: Run `python apps/api/cli_check.py --category music --source popmusic --query "محسن"` and verify MP3 stream and download URLs.

- [X] T025 [P] [US3] Create sample HTML search fixtures for music in `apps/api/tests/fixtures/popmusic_search.html` and `apps/api/tests/fixtures/popmusic_item.html`
- [X] T026 [P] [US3] Implement Nex1Music scraper plugin in `apps/api/sources/music/nex1music.py` (Server-rendered HTML, 320k/128k direct MP3s)
- [X] T027 [P] [US3] Implement Pop-Music scraper plugin in `apps/api/sources/music/popmusic.py`
- [ ] T028 [P] [US3] (BLOCKED-UPSTREAM) Implement RadioJavan scraper plugin in `apps/api/sources/music/radiojavan.py` (Cloudflare Bot Challenge - Solvable asynchronously via FlareSolverr background worker)
- [ ] T029 [P] [US3] (BLOCKED-UPSTREAM) Implement UpMusic scraper plugin in `apps/api/sources/music/upmusic.py` (Domain mismatch / parked)
- [X] T030 [US3] Implement music card template in `apps/api/web/templates/_music_card.html` with inline HTML5 audio player and 128k/320k download buttons
- [X] T031 [US3] Integrate music search and card rendering in `apps/api/web/app.py`
- [X] T032 [P] [US3] Write unit tests in `apps/api/tests/test_music_scrapers.py` verifying MP3 download and stream extraction from fixtures

**Checkpoint**: Primary media categories (Games, Music) functional and verified against live sources.

---

## Phase 6: User Story 4 - Opportunistic Movie Streaming (Priority: P2)

**Goal**: Detect unblocked direct video streams for movies and embed an inline HTML5 `<video>` player, falling back cleanly to download buttons without player errors.

- [X] T033 [US4] Implement direct stream validation helper (`is_directly_playable` + `validate_stream_url`) in `apps/api/sources/base.py` and integrate in `apps/api/web/app.py`
- [X] T034 [US4] Update `apps/api/web/templates/_movie_card.html` to conditionally render HTML5 `<video>` player when unproxied stream is present
- [X] T035 [P] [US4] Write unit tests in `apps/api/tests/test_streaming.py` ensuring blocked or CORS-restricted streams omit the embedded video player

---

## Phase 7: User Story 5 - Extensible Source Portal Management & Dynamic Redirects (Priority: P1 - Promoted)

**Goal**: Ensure domain mirror updates can be configured without code changes, and scrapers automatically follow 301/302 anti-filtering domain shifts.

**Independent Test**: Verified by `apps/api/tests/test_sources_config.py` asserting redirect tracking and dynamic env-var overrides.

- [X] T036 [US5] Implement automatic 301/302 redirect tracking and domain mirror update in `apps/api/http_client.py`
- [X] T037 [US5] Implement environment-variable and config overrides for source base URLs in `apps/api/sources/__init__.py`
- [X] T038 [US5] Implement `GET /api/sources` and `GET /health` endpoints in `apps/api/web/app.py`
- [X] T039 [P] [US5] Write unit tests in `apps/api/tests/test_sources_config.py` verifying base URL overrides and redirect updates

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final aesthetics, entrypoint, and validation

- [X] T040 [P] Implement clean, responsive dark/light CSS styling in `apps/api/web/static/style.css`
- [X] T041 Implement main Uvicorn application entrypoint in `apps/api/main.py`
- [X] T042 Execute automated test suite and live CLI smoke checks

---

## Status Summary

- **Completed Tasks**: 32 / 42 (Engineering features, base infrastructure, web UI, Games and Music [Downloadha, PopMusic, Nex1Music] scrapers, stream URL validation, persistent SQLite search index with FTS5, background crawler worker with FlareSolverr solver, configuration, and testing)
- **Blocked Upstream**: 10 / 42 (T010–T014, T017, T019, T021, T028, T029 — blocked due to upstream domain expiration [NXDOMAIN], parked landers, Cloudflare bot challenge, or reCAPTCHA). These sources can be individually re-enabled via environment variables (`MOVIE_FETCHER_ENABLE_<ID>=true` and `MOVIE_FETCHER_URL_<ID>=<url>`) as new working mirrors become available.
