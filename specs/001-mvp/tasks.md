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
- Exact file paths included in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic directory structure

- [X] T001 Create project package directory structure (`movie_fetcher/`, `movie_fetcher/sources/{movies,games,music}`, `movie_fetcher/metadata/`, `movie_fetcher/web/{static,templates}`, `tests/fixtures/`)
- [X] T002 Create `pyproject.toml` with dependencies (`fastapi`, `uvicorn`, `jinja2`, `httpx`, `selectolax`, `cachetools`) and dev dependencies (`pytest`, `pytest-asyncio`, `respx`)
- [X] T003 [P] Configure pytest and mock HTTP helpers in `tests/conftest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure and base types that MUST be complete before user stories

- [X] T004 Implement domain entities in `movie_fetcher/models.py` (`Category`, `SourceConfig`, `SearchQuery`, `MediaItem`, `MovieDownloadVariant`, `GameRelease`, `GamePartLink`, `MusicTrack`, `MusicDownloadVariant`, `CachedResult`)
- [X] T005 [P] Implement asynchronous HTTP client with custom headers, cookie jar, and redirect handling in `movie_fetcher/http_client.py`
- [X] T006 [P] Implement Persian/Arabic Unicode normalization and TTLCache in `movie_fetcher/cache.py`
- [X] T007 Implement `SourcePlugin` protocol and registry lookup in `movie_fetcher/sources/base.py` and `movie_fetcher/sources/__init__.py`
- [X] T008 Set up FastAPI application, Jinja2 template renderer, and static mount in `movie_fetcher/web/app.py` and `movie_fetcher/web/templates/base.html`
- [X] T009 [P] Implement CLI scraper smoke check runner in `movie_fetcher/cli_check.py`

**Checkpoint**: Foundation ready — user story implementation can begin

---

## Phase 3: User Story 1 - Movies Search & Download Extraction (Priority: P1)

*Status: Deferred to follow-up domain research pass. All 4 target movie domains (film2media, avamovie, zarfilm, mobomovie) are currently NXDOMAIN or parked pages. Registered as disabled in sources config.*

- [ ] T010 [P] [US1] (Deferred) Create sample HTML search fixtures for movies in `tests/fixtures/film2media_search.html` and `tests/fixtures/avamovie_search.html`
- [ ] T011 [P] [US1] (Deferred) Implement Film2Media scraper plugin in `movie_fetcher/sources/movies/film2media.py`
- [ ] T012 [P] [US1] (Deferred) Implement AvaMovie scraper plugin in `movie_fetcher/sources/movies/avamovie.py`
- [ ] T013 [P] [US1] (Deferred) Implement Zarfilm scraper plugin in `movie_fetcher/sources/movies/zarfilm.py`
- [ ] T014 [P] [US1] (Deferred) Implement MoboMovie scraper plugin in `movie_fetcher/sources/movies/mobomovie.py`
- [X] T015 [US1] Implement movie card template in `movie_fetcher/web/templates/_movie_card.html` categorizing resolution, codec, and dub/sub badges
- [X] T016 [US1] Implement movie search endpoint and results rendering in `movie_fetcher/web/app.py` and `movie_fetcher/web/templates/results.html`
- [ ] T017 [P] [US1] (Deferred) Write unit tests in `tests/test_movies_scrapers.py` verifying movie search and format extraction against fixtures

---

## Phase 4: User Story 2 - Complete Multi-Part Game Archive Extraction (Priority: P1) 🎯 MVP

**Goal**: Enable gamers to search games and receive complete, ordered split RAR archive links (Part 1..N) with file sizes, extraction passwords, and a one-click copy button.

**Independent Test**: Run `python -m movie_fetcher.cli_check --category games --source downloadha --query "noire"` and verify parts are sequential with archive password.

- [X] T018 [P] [US2] Create sample HTML search fixtures for games in `tests/fixtures/downloadha_search.html` and `tests/fixtures/downloadha_item.html`
- [ ] T019 [P] [US2] (Deferred - reCAPTCHA blocked) Implement YasDL scraper plugin in `movie_fetcher/sources/games/yasdl.py`
- [X] T020 [P] [US2] Implement Downloadha scraper plugin in `movie_fetcher/sources/games/downloadha.py` with multi-part parsing and password extraction
- [ ] T021 [P] [US2] (Deferred - domain offline) Implement Game2DL scraper plugin in `movie_fetcher/sources/games/game2dl.py`
- [X] T022 [US2] Implement game release card template in `movie_fetcher/web/templates/_game_card.html` displaying ordered parts, password copy button, and "Copy all links" action
- [X] T023 [US2] Integrate game search and card rendering in `movie_fetcher/web/app.py`
- [X] T024 [P] [US2] Write unit tests in `tests/test_games_scrapers.py` verifying sequential part ordering, gap detection, and password extraction

**Checkpoint**: User Story 2 fully functional and verified against live sources and offline fixtures.

---

## Phase 5: User Story 3 - Music Track Discovery, Preview, and Download (Priority: P1)

**Goal**: Enable music listeners to search Persian tracks, preview them via an inline HTML5 audio player, and download 128k/320k MP3s directly.

**Independent Test**: Run `python -m movie_fetcher.cli_check --category music --source popmusic --query "محسن"` and verify MP3 stream and download URLs.

- [X] T025 [P] [US3] Create sample HTML search fixtures for music in `tests/fixtures/popmusic_search.html` and `tests/fixtures/popmusic_item.html`
- [ ] T026 [P] [US3] (Deferred - SPA/non-SSR) Implement Nex1Music scraper plugin in `movie_fetcher/sources/music/nex1music.py`
- [X] T027 [P] [US3] Implement Pop-Music scraper plugin in `movie_fetcher/sources/music/popmusic.py`
- [ ] T028 [P] [US3] (Deferred - Cloudflare challenge) Implement RadioJavan scraper plugin in `movie_fetcher/sources/music/radiojavan.py`
- [ ] T029 [P] [US3] (Deferred - domain mismatch) Implement UpMusic scraper plugin in `movie_fetcher/sources/music/upmusic.py`
- [X] T030 [US3] Implement music card template in `movie_fetcher/web/templates/_music_card.html` with inline HTML5 audio player and 128k/320k download buttons
- [X] T031 [US3] Integrate music search and card rendering in `movie_fetcher/web/app.py`
- [X] T032 [P] [US3] Write unit tests in `tests/test_music_scrapers.py` verifying MP3 download and stream extraction from fixtures

**Checkpoint**: Primary media categories (Games, Music) functional and verified against live sources.

---

## Phase 6: User Story 4 - Opportunistic Movie Streaming (Priority: P2)

**Goal**: Detect unblocked direct video streams for movies and embed an inline HTML5 `<video>` player, falling back cleanly to download buttons without player errors.

- [ ] T033 [US4] (Deferred) Implement direct stream validation helper in `movie_fetcher/sources/base.py`
- [X] T034 [US4] Update `movie_fetcher/web/templates/_movie_card.html` to conditionally render HTML5 `<video>` player when unproxied stream is present
- [ ] T035 [P] [US4] (Deferred) Write unit tests in `tests/test_streaming.py` ensuring blocked or CORS-restricted streams omit the embedded video player

---

## Phase 7: User Story 5 - Extensible Source Portal Management & Dynamic Redirects (Priority: P1 - Promoted)

**Goal**: Ensure domain mirror updates can be configured without code changes, and scrapers automatically follow 301/302 anti-filtering domain shifts.

**Independent Test**: Verified by `tests/test_sources_config.py` asserting redirect tracking and dynamic env-var overrides.

- [X] T036 [US5] Implement automatic 301/302 redirect tracking and domain mirror update in `movie_fetcher/http_client.py`
- [X] T037 [US5] Implement environment-variable and config overrides for source base URLs in `movie_fetcher/sources/__init__.py`
- [X] T038 [US5] Implement `GET /api/sources` and `GET /health` endpoints in `movie_fetcher/web/app.py`
- [X] T039 [P] [US5] Write unit tests in `tests/test_sources_config.py` verifying base URL overrides and redirect updates

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final aesthetics, entrypoint, and validation

- [X] T040 [P] Implement clean, responsive dark/light CSS styling in `movie_fetcher/web/static/style.css`
- [X] T041 Implement main Uvicorn application entrypoint in `movie_fetcher/main.py`
- [X] T042 Execute automated test suite and live CLI smoke checks
