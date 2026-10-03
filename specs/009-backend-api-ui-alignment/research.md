# Research & Architectural Decisions: Backend API & UI Alignment

**Feature Branch**: `009-backend-api-ui-alignment`  
**Date**: 2026-10-03  
**Spec Reference**: `specs/009-backend-api-ui-alignment/spec.md`

---

## 1. Concurrency & Storage: SQLite WAL Mode for Multi-Worker Architecture

### Decision
Configure SQLite with Write-Ahead Logging (`PRAGMA journal_mode = WAL;`) and a busy timeout (`PRAGMA busy_timeout = 10000;`) in `apps/api/db.py`. Maintain separate connection instances per process/thread.

### Rationale
- The architecture requires concurrent access: the FastAPI web process serves user search and catalog queries while three background worker processes (`movies`, `games`, `music`) continuously write crawled items and crawl state.
- In default rollback journal mode, writers block readers completely. In WAL mode, SQLite supports multiple concurrent readers alongside a concurrent writer.
- Adheres strictly to Constitution Principle II (Simplicity & Monorepo Platform Structure: SQLite with FTS5 and in-memory TTL caching satisfy persistence without Redis/Postgres infrastructure).

### Alternatives Considered
- **PostgreSQL / MySQL**: Rejected per Constitution Principle II (YAGNI / simplicity). External database servers introduce infrastructure dependencies, network hops, and operational overhead unwarranted for link aggregation.
- **Single Threaded Event-Loop SQLite**: Rejected because long-running background scraping jobs and heavy HTML extraction should run in dedicated daemon processes without starving FastAPI's async event loop.

---

## 2. AI-Assisted Scraping & Structured Extraction with LangChain

### Decision
Integrate `langchain-core` with standard chat model adapters (`langchain-openai` / `langchain-anthropic` or generic OpenAI-compatible endpoint configured via `LLM_API_KEY`, `LLM_MODEL`, and `LLM_BASE_URL`). 
Preprocess raw HTML with `selectolax` (stripping `<script>`, `<style>`, `<svg>`, header, and footer trees) before passing targeted content blocks into `ChatPromptTemplate` combined with `ChatModel.with_structured_output(PydanticSchema)`.

### Rationale
- Iranian media portals have diverse, unstandardized HTML layouts. Regex and rigid CSS selectors frequently break when portals redesign or disguise download sections.
- LangChain's `with_structured_output` guarantees typed JSON adhering strictly to Pydantic models (`MovieExtractionResult`, `GameReleaseExtractionResult`, `MusicTrackExtractionResult`).
- HTML pruning via `selectolax` reduces token payload by 75–90%, keeping API inference costs low and inference latencies under 2 seconds.
- Fallback strategy: If extraction fails or times out, the item is persisted to `extraction_dead_letter` for operator inspection, avoiding brittle heuristic fallbacks per user clarification.

### Alternatives Considered
- **Raw OpenAI/Anthropic SDK calls**: Rejected because LangChain provides unified model switching across OpenAI, Anthropic, and local endpoints without changing schema definitions or tool code.
- **Pure CSS/Regex Scrapers**: Maintained as fast path for pristine, standard pages, but insufficient for unstructured download grids and varying multi-part archive formats.

---

## 3. Search Strategy: Offline-First Hybrid with On-Demand Movie Fallback

### Decision
Refactor `apps/api/web/app.py:api_search_media` and `apps/api/db.py`:
1. **Index-First Lookup**: All searches across `movies`, `games`, and `music` query the local SQLite FTS5 database (`search_fts` joined with `media_items` and download variant tables). If matching records are found, return immediately with `is_cached=True`.
2. **Category Routing**:
   - **Music & Games**: Always served from the local database index. If 0 items match, return an empty list with a warning that the title is being indexed by background crawlers.
   - **Movies**: If the local database index returns 0 matches (or if `refresh=true`), trigger live on-demand scraper execution across movie sources within the 10-second request budget, return live results, and immediately upsert them into SQLite with FTS5 indexing.

### Rationale
- Instantaneous search response (<50ms) for known and popular titles.
- Drastically reduces outbound network traffic and risk of upstream rate-limiting on high-frequency queries.
- Ensures movie catalog discovery never suffers from crawler staleness while keeping game and music searches entirely local.

### Alternatives Considered
- **Always Live Search with Cache**: Current implementation (`GLOBAL_CACHE` in memory + SQLite write-through). Rejected because live scraper fan-out takes 2–5 seconds per request and fails if upstream portals are slow or degraded.
- **100% Offline Search for All Categories**: Rejected because movie releases churn rapidly and user searches often target titles published minutes prior.

---

## 4. Continuous Background Crawlers (Three Category Daemons)

### Decision
Extend `apps/api/worker.py` into a multi-daemon service supporting `--category movies`, `--category games`, and `--category music` (or `--category all` concurrently via `asyncio.gather`).
Each category worker:
1. Iterates over active source plugins registered for that category.
2. Crawls recent pagination indexes or RSS/sitemap feeds.
3. Checks if `page_url` exists in `media_items` and whether `last_seen` is stale (> 24 hours).
4. Fetches and processes unindexed or updated pages (using LangChain for non-standard layouts).
5. Upserts extracted items, download variants, and game parts into SQLite.
6. Updates `crawl_state` and records operational health metrics.
7. Sleeps for a configurable interval (`CRAWL_INTERVAL_SECONDS`, default 300s) before repeating.

### Rationale
- Decouples long-running scrape operations from client request loops.
- Category isolation prevents slow scrapers in one domain (e.g., Cloudflare-protected music portals) from starving movie or game updates.
- Adheres to Constitution Principle I (Module Isolation) and Principle II (Monorepo Simplicity).

### Alternatives Considered
- **Celery / Redis / RabbitMQ queue**: Rejected per Constitution Principle II. An external task broker adds dependencies, Redis/Erlang runtimes, and deployment overhead. A lightweight asyncio/multiprocess loop over SQLite handles Linkschin's source volume effortlessly.

---

## 5. Operator Authentication & Authorization (JWT Bearer)

### Decision
Implement lightweight JWT authentication in `apps/api/web/auth.py` using `PyJWT` or `python-jose` with `HS256` symmetric signing.
- Endpoint: `POST /api/auth/login` accepting `{ "username": "...", "password": "..." }`, returning `{ "access_token": "...", "token_type": "bearer", "expires_in": 86400 }`.
- Credentials configured via environment variables (`OPERATOR_USERNAME`, `OPERATOR_PASSWORD_HASH`, `JWT_SECRET_KEY`).
- FastAPI dependency `get_current_operator` validates `Authorization: Bearer <token>` on protected endpoints:
  - `PATCH /api/sources/{id}` (mirror / address updates)
  - `PATCH /api/sources/{id}/toggle` (enable / disable)
  - `GET /api/admin/suggestions` (queue triage)
  - `PATCH /api/admin/suggestions/{id}` (approve / reject)

### Rationale
- Per user clarification: "JWT Bearer Token".
- Eliminates cross-origin cookie issues (`SameSite`, CORS credentials) between Next.js frontend (`localhost:3000`) and FastAPI backend (`localhost:8000`).
- Stateless, fast, easily stored in browser memory/storage for the operator console.

### Alternatives Considered
- **HttpOnly Cookies**: Rejected due to cross-origin local development complexity.
- **Shared API Key Header**: Rejected by user decision in favor of full user auth.

---

## 6. YouTube to MP3: Immediate Streaming with Zero Server Storage

### Decision
Implement `POST /api/convert`, `GET /api/convert/{id}`, and `GET /api/download/{id}` using `yt-dlp` and `ffmpeg`:
1. `POST /api/convert`: Accepts YouTube URL, validates format, checks client rate limit (20 req/hour/IP via in-memory bucket or SQLite), assigns a unique job UUID, and schedules async background audio extraction into a dedicated temporary folder (`/tmp/linkschin_mp3/{job_id}/`).
2. `GET /api/convert/{id}`: Polls progress (0–100%) and status (`queued`, `processing`, `completed`, `failed`).
3. `GET /api/download/{id}`: Streams the completed `.mp3` file via FastAPI `FileResponse` with `Content-Disposition: attachment; filename="..."`.
4. **Immediate Deletion**: A background cleanup task attached to `FileResponse` deletes the temporary file and parent directory immediately after the stream closes. A scheduled watchdog cleans any abandoned jobs older than 15 minutes.

### Rationale
- Resolves the Linkschin Constitution Principle III conflict (No Media Relaying) as an explicit, isolated utility exception while strictly upholding the user clarification: zero permanent server-side media retention.
- No media files remain on the server; disk space is strictly bounded.

### Alternatives Considered
- **Server File Storage with 24h retention**: Rejected by user decision in favor of immediate streaming.
- **Client-side WebAssembly ffmpeg**: Rejected because browser YouTube scraping is blocked by CORS, bot detection, and mobile memory limits.

---

## 7. Intelligent Assistant: LangChain Agent with Database Tools

### Decision
Implement `POST /api/chat` using LangChain's `create_tool_calling_agent` or modern `AgentExecutor` / graph runner:
- Tools exposed to LLM:
  1. `search_catalog(query: str, category: str, quality: str | None, dub: bool | None)`: Queries local SQLite database.
  2. `check_source_health(source_id: str | None)`: Reads `source_health` table.
  3. `inspect_game_archive(game_title: str)`: Inspects `game_releases` and `game_parts` for missing sequential gaps and extraction passwords.
- Streaming: Returns standard Server-Sent Events (SSE) emitting text deltas and structured `media_card` payloads for matched items.

### Rationale
- Satisfies user clarification: "LLM with DB Tools".
- Grounded entirely in verified platform data; prevents hallucinations regarding release qualities, active sources, or download passwords.

---

## 8. Centralized Adaptive Scraping Queue & Rate Limiter (User Story 6)

### Decision
Implement an in-memory asynchronous priority queue (`AdaptiveCrawlQueue` in `apps/api/crawler/queue.py`) paired with per-domain rate limiting and exponential backoff (`DomainThrottlePolicy`).
- **Priority Scheduling**: Tasks carry priority weights:
  - `Priority 0`: Real-time user on-demand search requests (preempts background crawls).
  - `Priority 1`: Scheduled continuous category crawl tasks (movies, games, music).
- **Per-Domain Concurrency Limits**: Each portal domain has a concurrency semaphore (`max_concurrency = 1` or `2`).
- **Adaptive Backoff**:
  - Monitors response status codes and request latency per domain.
  - On HTTP 429 (Too Many Requests), HTTP 503, or connection timeouts, the domain's throttle policy activates exponential backoff: base delay 2.0s -> 4.0s -> 8.0s -> 16.0s (capped at 60.0s) with random jitter (+/- 20%).
  - Does NOT block or delay crawler workers querying other domains.

### Rationale
- Fulfills User Story 6 requirements for centralized coordination, priority on-demand search execution, and domain-level anti-ban protection.
- Prevents resource starvation on shared network interfaces.
- Decouples task enqueuing from task execution.

### Alternatives Considered
- **Redis / Celery Priority Queues**: Rejected per Constitution Principle II (Simplicity & Monorepo Platform Structure). An in-process `asyncio.PriorityQueue` with SQLite persistence for uncompleted background jobs handles priority scheduling without adding Redis dependencies.

---

## 9. Strict AI-Assisted Structured Extraction & Dead Letter Queue (DLQ) Reliability (User Story 7)

### Decision
1. **Strict LangChain Extraction Schemas**:
   - Extraction chains employ LangChain's `ChatModel.with_structured_output(PydanticSchema, strict=True)`.
   - Pydantic models strictly validate all extracted attributes (integer part numbers, valid HTTP/HTTPS URLs, standardized resolution/codec strings, and normalized entity names).
2. **Dead Letter Queue (DLQ) Architecture**:
   - When an extraction fails (LLM API rate limit, JSON schema validation error, unparseable layout), the worker catches the error immediately without applying fragile regex heuristics.
   - The raw HTML payload, source ID, page URL, error message, and timestamp are inserted into the SQLite `extraction_dead_letter` table with `status = 'pending'`, `retry_count = 0`, and `next_retry_at = now() + 60s`.
3. **Automated DLQ Re-processor**:
   - A background DLQ retry task polls `extraction_dead_letter` for items where `status = 'pending'` and `next_retry_at <= now()`.
   - Re-runs extraction with exponential backoff (retry count up to 5).
   - Upon successful extraction, upserts records into `media_items` and download variant tables, and marks the DLQ item `status = 'resolved'`.
   - After maximum retries, marks `status = 'failed'` for operator manual triage.

### Rationale
- Fulfills User Story 7 requirements for strict schema enforcement, zero dropped listings, and automated retry resilience.
- Guarantees data integrity in the primary catalog while isolating transient AI failures.

