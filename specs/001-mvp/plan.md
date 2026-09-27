# Implementation Plan: Iranian Multi-Media Direct Link Aggregator (MVP)

**Branch**: `001-mvp` | **Date**: 2026-09-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-mvp/spec.md`

## Summary

Build a local, server-rendered multi-media fetcher and aggregator web application targeting Iranian sources for **Movies, Games, and Music**. The application provides tab-based search across pluggable website scrapers, extracting direct download links categorized by format/quality/part and offering opportunistic in-browser media playback (instant audio preview for music; direct stream embed for movies when unblocked by CORS) without any server-side media proxying.

## Technical Context

- **Language/Version**: Python 3.11+
- **Primary Dependencies**:
  - `fastapi` & `uvicorn`: Lightweight async web server and request handling.
  - `jinja2`: Server-rendered HTML templates (no Node/npm/SPA build pipeline).
  - `httpx`: Asynchronous HTTP client with connection pooling, custom headers, cookie handling, and 301/302 redirect following.
  - `selectolax`: Fast C-based HTML parsing for reliable DOM extraction.
  - `cachetools`: In-memory `TTLCache` (45-minute expiry) for query caching.
  - `pytest` & `respx`: Unit and contract testing with mocked HTTP fixtures.
- **Storage**: In-memory cache only; zero persistent database dependencies.
- **Testing**: `pytest`, `pytest-asyncio`, `respx` fixture tests, plus dedicated `cli_check.py` smoke runner.
- **Target Platform**: Cross-platform (Linux/macOS/Windows) run locally or self-hosted.
- **Project Type**: Web service with server-rendered UI and CLI smoke utility.
- **Performance Goals**: Cached searches < 2 seconds; multi-source uncached searches < 12 seconds.
- **Constraints**:
  - Zero server bandwidth consumed by media relaying (no video/audio proxying).
  - Free public tiers only (no VIP account pooling or paywall bypass).
  - Enforced per-source scraping timeout budget (7s per source, 10s global category deadline).
- **Scale/Scope**: 11 initial source plugins across 3 categories:
  - *Movies*: Film2Media, AvaMovie, Zarfilm, MoboMovie.
  - *Games*: YasDL, Downloadha, Game2DL / PersianDL.
  - *Music*: Nex1Music, Pop-Music, RadioJavan, UpMusic.

## Constitution Check

*GATE: Evaluated against `.specify/memory/constitution.md`.*

| Principle / Rule | Compliance Status | Justification |
|---|---|---|
| I. Library / Module Isolation | PASS | Scrapers are decoupled into standalone plugins under `movie_fetcher/sources/` implementing `SourcePlugin`. |
| II. Simplicity / YAGNI | PASS | Server-rendered HTML using Jinja2; no SPA bundlers, no external database, no Redis cache. |
| III. No Media Relaying | PASS | Server never buffers, proxies, or stores media files. All stream and download links route directly to upstream CDNs. |
| IV. Testability | PASS | All scrapers verifiable offline using saved HTML fixtures in `tests/fixtures/` with `respx`. |

## Project Structure

### Documentation (`specs/001-mvp/`)

```text
specs/001-mvp/
├── spec.md              # Feature specification
├── plan.md              # This implementation plan
├── research.md          # Technical research & decisions (Phase 0)
├── data-model.md        # Entities, schemas, validation rules (Phase 1)
├── quickstart.md        # Validation scenarios & run guide (Phase 1)
├── contracts/           # Interface contracts (Phase 1)
│   ├── scraper-plugin.md # Scraper protocol & lifecycle rules
│   └── web-routes.md    # HTTP routes and query parameter contracts
└── checklists/
    └── requirements.md  # 16/16 quality checklist verification
```

### Source Code (`movie_fetcher/`)

```text
movie_fetcher/
├── __init__.py          # Package initialization & version
├── models.py            # Category, MediaItem, DownloadVariants, GameRelease, SourceConfig
├── cache.py             # TTLCache wrapper keyed by (category, query)
├── http_client.py       # Async HTTP client with headers, cookie jar, redirect follow
├── metadata/
│   ├── __init__.py
│   ├── tmdb.py          # Movie title aliases, year, poster enrichment
│   └── rawg.py          # Game title, year, developer enrichment
├── sources/
│   ├── __init__.py      # Global SOURCE_REGISTRY & get_sources_for_category()
│   ├── base.py          # SourcePlugin protocol & shared extraction helpers
│   ├── movies/
│   │   ├── __init__.py
│   │   ├── film2media.py
│   │   ├── avamovie.py
│   │   ├── zarfilm.py
│   │   └── mobomovie.py
│   ├── games/
│   │   ├── __init__.py
│   │   ├── yasdl.py
│   │   ├── downloadha.py
│   │   └── game2dl.py
│   └── music/
│       ├── __init__.py
│       ├── nex1music.py
│       ├── popmusic.py
│       ├── radiojavan.py
│       └── upmusic.py
├── web/
│   ├── __init__.py
│   ├── app.py           # FastAPI routes: /, /search, /health, /api/sources
│   ├── static/
│   │   └── style.css    # Clean, minimalist dark/light CSS
│   └── templates/
│       ├── base.html    # Layout with header, tabs, search bar
│       ├── results.html # Search results loop with media cards
│       ├── _movie_card.html
│       ├── _game_card.html
│       └── _music_card.html
├── cli_check.py         # Standalone CLI smoke runner for testing scrapers directly
└── main.py              # Entrypoint (uvicorn runner)

tests/
├── conftest.py          # Shared test fixtures & respx mock setup
├── fixtures/            # Static HTML snapshots of target site search pages
│   ├── film2media_search.html
│   ├── avamovie_search.html
│   ├── yasdl_search.html
│   ├── downloadha_search.html
│   └── nex1music_search.html
├── test_models.py       # Data model validations & part sequence checks
├── test_cache.py        # TTLCache expiration & key normalization
└── test_scrapers.py     # Parser tests against HTML fixtures
```

## Complexity Tracking

No constitution violations or unwarranted abstractions. Single Python package with in-memory caching and server-rendered templates.

## Implementation Phases

### Phase 1: Core Foundation & Scraper Engine
1. Set up `pyproject.toml` with `fastapi`, `uvicorn`, `jinja2`, `httpx`, `selectolax`, `cachetools`.
2. Implement `models.py` (data structures for all three media categories).
3. Implement `http_client.py` and `cache.py` with Persian string normalization.
4. Implement `sources/base.py` and registry mechanism in `sources/__init__.py`.

### Phase 2: Category Scrapers
1. **Movies Scrapers**: `film2media.py`, `avamovie.py`, `zarfilm.py`, `mobomovie.py`.
2. **Games Scrapers**: `yasdl.py`, `downloadha.py`, `game2dl.py` with multi-part sequential parser and password extraction.
3. **Music Scrapers**: `nex1music.py`, `popmusic.py`, `radiojavan.py`, `upmusic.py` with MP3 stream extraction.
4. Build `cli_check.py` to independently smoke-test scrapers from the terminal.

### Phase 3: Web Interface & Presentation
1. Set up FastAPI routes in `web/app.py` for `/`, `/search`, and `/health`.
2. Author Jinja2 templates (`base.html`, `results.html`, and cards for Movies, Games, Music).
3. Implement inline HTML5 `<audio>` player for music and opportunistic `<video>` player for movies.
4. Implement "Copy all links" and "Copy password" clipboard actions for games.

### Phase 4: Automated Testing & Verification
1. Add offline HTML fixtures under `tests/fixtures/`.
2. Write unit tests in `tests/test_scrapers.py` validating parser accuracy.
3. Validate end-to-end user journeys against `quickstart.md`.
