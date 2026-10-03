# Implementation Plan: Backend API and UI Alignment & Gap Resolution

**Branch**: `009-backend-api-ui-alignment` | **Date**: 2026-10-03 | **Spec**: [specs/009-backend-api-ui-alignment/spec.md](spec.md)

**Input**: Feature specification from `/specs/009-backend-api-ui-alignment/spec.md`

---

## Summary

This plan aligns the Linkschin backend API with the web UI's functional requirements and eliminates all hardcoded fixtures. The core implementation introduces:
1. **Persistent Search Indexing (SQLite FTS5 + WAL)**: Every live search result is immediately indexed for sub-50ms repeat/similar queries.
2. **Hybrid Search Strategy**: Music and Games are served offline-first from the continuously updated database; Movies search offline first and fall back to on-demand live scraping only when zero database records match.
3. **Three Category Background Crawlers with LangChain**: Continuous daemons for movies, games, and music that use LangChain structured extraction schemas to parse complex/unstructured portal HTML into typed media records and direct links.
4. **Dynamic Catalog Feeds**: Real database-driven trending and latest release endpoints for home shelves.
5. **Operator Authentication & Registry Management**: JWT Bearer token authentication protecting source mirror/address updates and community suggestion triage.
6. **YouTube to MP3 Audio Utility**: Asynchronous conversion with immediate single-use streaming and zero persistent server storage.
7. **Conversational Assistant**: LangChain agent equipped with catalog search and source health database tools.
8. **Centralized Adaptive Scraping Queue (User Story 6)**: Priority queue scheduler preempting background crawls for live search queries, with per-domain concurrency limits and adaptive backoff on 429/timeout.
9. **Strict AI Extraction & DLQ Reliability (User Story 7)**: LangChain Pydantic schemas with dead-letter queue persistence and automated retry mechanism for failed extractions.

---

## Technical Context

**Language/Version**: Python 3.12 (backend API & workers), TypeScript 5.7 / React 19 / Next.js 15 (web frontend)

**Primary Dependencies**:
- Backend: `fastapi>=0.110.0`, `uvicorn[standard]>=0.28.0`, `httpx>=0.28.0`, `selectolax>=0.3.21`, `langchain-core`, `langchain-openai` (or compatible API adapter), `pyjwt>=2.8.0`, `passlib[argon2]`, `yt-dlp`
- Frontend: `next@15.2.0`, `lucide-react`, `tailwindcss`

**Storage**: SQLite 3 with FTS5 trigram extension, WAL mode (`PRAGMA journal_mode = WAL;`), busy timeout 10000ms. Database file at `apps/api/data/index.db`. Zero external databases or message brokers.

**Testing**: `pytest`, `pytest-asyncio`, `respx` (offline mock fixtures for scrapers), `node --test` for web unit tests.

**Target Platform**: Linux (Arch / Debian), Docker container, Kubernetes deployment.

**Project Type**: Monorepo with FastAPI service (`apps/api`), Next.js application (`apps/web`), and background crawler workers (`apps/api/worker.py`).

**Performance Goals**:
- Sub-50ms response for cached/indexed search queries across all categories.
- Sub-100ms preemption of background crawl tasks by live user searches.
- Strict 10-second budget for live movie on-demand scraper fallback.
- Sub-45-second conversion for standard (<5 min) YouTube music videos.
- 99.5% uptime for continuous background crawler daemons.
- 100% dead-letter queue capture of failed extractions with automated backoff retry.

**Constraints**:
- Linkschin Constitution compliance: Zero media relaying for general media (direct CDN links only); module isolation; stdlib SQLite only; NFKC normalization.
- Ephemeral storage: YouTube MP3 files deleted immediately upon client stream completion.

**Scale/Scope**:
- 20+ movie portals, 20+ music portals, 8+ game portals.
- Thousands of indexed releases across categories.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Plan Status | Justification / Mitigation |
| :--- | :--- | :--- | :--- |
| **I. Module Isolation** | Standalone scrapers under `sources/`. Zero cross-scraper imports. | **PASS** | Each scraper plugin remains independent. Background crawlers interface via `BaseSourcePlugin` protocol. |
| **II. Simplicity & Monorepo Platform Structure** | Minimal dependencies, Turborepo monorepo, stdlib SQLite + FTS5, in-memory caching. No external Redis/RabbitMQ/Postgres. | **PASS** | SQLite WAL mode supports concurrent background worker writes and API reads. Priority queues and domain throttles managed in-process without external brokers. |
| **III. No Media Relaying (NON-NEGOTIABLE)** | Server must NEVER buffer, proxy, download, or relay media payloads. Direct client-to-CDN only. | **PASS (with isolated utility exception)** | General aggregation routes 100% directly to upstream CDNs. YouTube to MP3 utility is an isolated exception with immediate streaming and zero permanent server storage. |
| **IV. Testability & Offline Verification** | Scrapers verifiable offline using static HTML fixtures with mocked HTTP clients (`respx`). | **PASS** | All new parsers and LangChain extraction chains include static HTML fixtures and mock LLM test suites. |

---

## Project Structure

### Documentation (this feature)

```text
specs/009-backend-api-ui-alignment/
├── plan.md              # Implementation plan
├── research.md          # Architectural research & decisions
├── data-model.md        # Relational schema & Pydantic extraction models
├── quickstart.md        # End-to-end validation scenarios
├── contracts/           # OpenAPI service contracts
│   ├── search-api.yaml
│   ├── sources-api.yaml
│   ├── youtube-mp3-api.yaml
│   ├── chat-api.yaml
│   ├── auth-api.yaml
│   └── dlq-api.yaml
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Source Code (repository root)

```text
apps/api/
├── main.py                      # Uvicorn entrypoint
├── models.py                    # Domain dataclasses & Pydantic extraction schemas
├── db.py                        # SQLite WAL schema, FTS5 queries, upsert operations
├── cache.py                     # NFKC text normalization & in-memory cache
├── http_client.py               # AsyncHttpClient with strict timeouts
├── worker.py                    # Multi-daemon background crawler service (movies, games, music)
├── crawler/
│   ├── __init__.py
│   ├── queue.py                # Adaptive priority queue (User Story 6)
│   └── throttle.py             # Domain-level concurrency & backoff policy (User Story 6)
├── web/
│   ├── __init__.py
│   ├── app.py                  # FastAPI route handlers (search, sources, catalog, convert, chat)
│   ├── auth.py                 # JWT Bearer token authentication & dependency guards
│   ├── catalog.py              # Dynamic trending & latest catalog query logic
│   ├── convert.py              # YouTube to MP3 extraction & streaming handlers
│   └── chat.py                 # LangChain conversational agent with DB tools
├── extraction/
│   ├── __init__.py
│   ├── chains.py               # LangChain structured output chains for HTML extraction
│   └── dead_letter.py          # Failed extraction persistence & DLQ retry worker (User Story 7)
└── sources/
    ├── base.py                 # BaseSourcePlugin interface
    ├── movies/                 # Movie scrapers
    ├── games/                  # Game scrapers
    └── music/                  # Music scrapers

apps/web/
├── src/
│   ├── app/
│   │   ├── page.tsx            # Homepage connecting to live catalog & search
│   │   ├── sources/page.tsx    # Sources console calling /api/sources & /api/sources/suggest
│   │   └── youtube-to-mp3/     # MP3 converter calling /api/convert & /api/download
│   ├── components/
│   │   ├── AiAssistant.tsx     # Chat assistant calling /api/chat
│   │   ├── Header.tsx          # Clean navigation bar without duplicate home tab
│   │   ├── StaticSections.tsx  # Dynamic shelf rendering from live catalog API
│   │   └── cards/              # Media cards consuming live variant structures
│   └── lib/
│       ├── api.ts              # API client methods for all backend endpoints
│       └── catalog.ts          # Normalization helpers & type interfaces
```

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| **Media Relaying Exception (YouTube to MP3)** | User explicitly requested an authentic YouTube to MP3 audio converter utility. | Client-side conversion fails due to browser CORS, bot detection, and mobile memory limits. Immediate streaming with zero server storage strictly bounds disk usage. |
| **LangChain Dependency** | Scraped Iranian portals frequently change layouts; rigid CSS/regex fails to parse complex download matrices and archive part sequences. | Hand-crafting hundreds of fragile regexes for 40+ media portals creates constant maintenance debt; LLM structured extraction parses diverse layouts reliably. |
