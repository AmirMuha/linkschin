# Technical Research & Decisions: Iranian Multi-Media Direct Link Aggregator (MVP)

- **Feature**: `001-mvp`
- **Date**: 2026-09-27
- **Status**: Complete (All technical unknowns resolved)

## Decision 1: Language & Core Stack

### Decision
Python 3.11+ using `FastAPI`, `Uvicorn`, and `Jinja2` for server-side HTML rendering.

### Rationale
- **Fast scraper iteration**: Target Iranian media sites rotate domains and tweak markup frequently. Python offers the fastest edit-test-debug loop for adjusting DOM selectors and regex without compilation steps.
- **Unified stack**: Server-rendered HTML via Jinja2 eliminates the complexity of a separate Node.js build pipeline, npm dependencies, or SPA hydration for an MVP.
- **Asynchronous concurrency**: Native `async`/`await` enables querying 3–4 upstream sources simultaneously without blocking the server event loop.

### Alternatives Considered
- *Go*: Single binary and low memory footprint, but rigid compilation and static typing slow down the rapid patching required when target HTML structures shift.
- *TypeScript / Next.js*: Excellent for dynamic SPAs, but introduces Node modules, bundler tooling, and unnecessary architectural complexity for an MVP that only renders search results and link lists.

---

## Decision 2: HTTP Client & HTML Parsing

### Decision
`httpx` (async) paired with `selectolax` (Modest engine).

### Rationale
- **HTTPX**:
  - Full async support (`httpx.AsyncClient`) with connection pooling.
  - Native cookie jar handling and customizable headers (User-Agent rotation, Referer emulation).
  - Explicit control over 301/302 redirect following to capture domain migration mirrors automatically.
- **Selectolax**:
  - Built on the C-based Modest/Lexbor HTML5 parsing engine, 5x–10x faster than BeautifulSoup4 and significantly lighter on CPU/memory during high-concurrency scraping.
  - Robust against malformed and incomplete HTML commonly found on legacy media blogs.

### Alternatives Considered
- *BeautifulSoup4 / lxml*: High memory footprint and slower parsing speed across multiple concurrent pages.
- *Playwright / Puppeteer*: Headless browsers consume hundreds of megabytes of RAM per instance. Unnecessary for the initial target sites which expose links in static HTML or simple AJAX endpoints.

---

## Decision 3: Concurrency & Scraping Timeout Budget

### Decision
`asyncio.gather` with a bounded per-source timeout and global deadline using `asyncio.wait_for`.

### Rationale
- When a user submits a search in the "Movies" tab, 4 scrapers (`Film2Media`, `AvaMovie`, `Zarfilm`, `MoboMovie`) execute in parallel.
- Setting an individual scraper timeout of 7 seconds and an overall category budget of 10 seconds guarantees that a hanging or blocked upstream site never stalls the user's search.
- Failed or timed-out sources are caught via `return_exceptions=True` and surfaced as non-blocking source warnings in the UI.

### Alternatives Considered
- *Sequential scraping*: Unacceptable latency (4 sources * 3s = 12s+ minimum).
- *Background task queues (Celery/RQ)*: Adds Redis/RabbitMQ infrastructure debt when synchronous async concurrency directly satisfies the <12s target.

---

## Decision 4: In-Memory Caching Strategy

### Decision
In-process `cachetools.TTLCache` keyed by `(category, normalized_query)` with a 45-minute TTL and max size of 2,000 entries.

### Rationale
- Iranian media download links (especially tokenized CDN links) often expire within a few hours. A 30–60 minute TTL prevents returning dead links while eliminating redundant scraping for popular queries.
- Zero external dependencies: no Redis or memcached server required to run or self-host the application.

### Alternatives Considered
- *SQLite / PostgreSQL persistent cache*: Adds database migrations and schema maintenance for ephemeral data that naturally rots within hours.
- *Redis*: Unjustified infrastructure requirement for a local/self-hosted MVP.

---

## Decision 5: Multi-Part Game Archive & Password Extraction

### Decision
Structured regex extraction pipeline parsing part numbering (`Part01`, `Part1`, `Part 01`, `پارت ۱`), file size patterns (`\d+(\.\d+)?\s*(GB|MB|گیگابایت)`), and archive password blocks (`رمز فایل`, `password:`, `pass:`).

### Rationale
- Gaming sites (YasDL, Downloadha) follow predictable text conventions for repacks and split archives.
- Grouping parts sequentially into a structured object (`GameRelease`) enables one-click "Copy all links" and prevents missing-part gaps from going unnoticed.

---

## Decision 6: Audio & Video Streaming Playback

### Decision
- **Music**: Direct HTML5 `<audio>` tag embedding the upstream MP3 URL (128kbps or 320kbps).
- **Movies**: Opportunistic check. If the upstream link is an unauthenticated MP4/HLS link without CORS/hotlink blockades, embed `<video>` player; otherwise, fall back strictly to direct download buttons.
- **Zero proxying**: The application server never relays media traffic.

### Rationale
- MP3 files on Persian music blogs are overwhelmingly served without restrictive CORS headers, playing cleanly in standard browser audio controls.
- Video streams frequently enforce token or domain referrers. Refusing to run a server-side media relay protects the host from bandwidth saturation and hosting termination.
