# Feature Specification: Backend API and UI Alignment & Gap Resolution

**Feature Branch**: `009-backend-api-ui-alignment`

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "backend api should align and implement the functionality that the current UI needs, find the gaps. the result of each search should be indexed and stored for later similar searches for fast responses, I also need background jobs that constantly scrape the web for musics, so only search for the movies live and on demand only when no results of the offline database is found, the background job which is frequently looking and scraping the web for movies, games, musics and their links with the help of AI (use langchain for it), should be on constantly running and scraping, one job for each category, and I need structured storage of links and their data with the help of llms and langchain."

## Clarifications

### Session 2026-10-03
- **Q: What storage retention policy should the backend enforce for converted YouTube MP3 files?**  
  → **A: Immediate Stream (No Store)**. Converted audio is streamed directly to the requesting client upon job completion and immediately purged; the server maintains zero persistent media files. Job metadata remains in conversion history.
- **Q: How should administrative operations (source mirror edits, enable/disable toggles) be authorized?**  
  → **A: Full User Auth (JWT Bearer Tokens)**. Source registry configuration edits and operator review triage are protected by authenticated user sessions/tokens using JWT Bearer tokens (`Authorization: Bearer <token>`) with an `/api/auth/login` endpoint, enabling clean cross-origin handling between frontend and API.
- **Q: Which architecture should power the conversational search assistant?**  
  → **A: LLM with DB Tools**. The assistant is powered by an LLM agent using LangChain with direct tool-calling access to live catalog search and source health queries.
- **Q: What is the search strategy across categories?**  
  → **A: Hybrid Cache-First Strategy**.  
  - **All Categories**: All search results are indexed and stored in the persistent database to accelerate subsequent identical or similar searches.
  - **Music & Games**: Always served offline-first from the continuously scraped local database index.
  - **Movies**: Served offline-first from the database; on-demand live scraping is triggered **only when no results are found in the offline database**.
- **Q: How should continuous background scraping and link extraction operate?**  
  → **A: Three Category-Specific Background Daemons with LangChain**. Dedicated background jobs (one for movies, one for games, one for music) run continuously, scraping portals and utilizing LangChain with LLMs to parse unstructured web content into typed, structured link metadata.
- **Q: Which LLM provider and deployment model should the LangChain extraction workers and AI Assistant target by default?**  
  → **A: Cloud API (.env)**. LangChain workers and the conversational assistant default to cloud LLM providers configured via environment variables (`LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`), enabling high-precision structured JSON extraction without requiring local GPU infrastructure.
- **Q: How should the background crawlers handle items when LangChain LLM structured extraction fails or times out?**  
  → **A: Dead-letter Queue**. Failed or timed-out extractions are skipped immediately without heuristic fallbacks and preserved in an extraction dead-letter queue table with raw HTML and error diagnostics for administrator inspection.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Instant Search with Persistent Indexing & On-Demand Fallback (Priority: P1)

As a media seeker on Linkschin, I want instant search results powered by a persistent local database, with movies falling back to live web scraping only when the database lacks matches, so that my queries resolve in milliseconds while guaranteeing discovery for newer or niche movie titles.

**Why this priority**: Search speed and result completeness define user satisfaction. Serving from an indexed database eliminates multi-second scraper fan-outs on repeat or known queries, while live fallback protects movie catalog freshness.

**Independent Test**: Can be tested by searching for a movie not present in the local database, verifying that live scrapers execute and return results, confirming that the results are immediately indexed in SQLite, and executing the same query again to verify sub-50ms offline database resolution.

**Acceptance Scenarios**:

1. **Given** a search query for any category (movies, games, music), **When** the query matches records in the local database index, **Then** results are returned immediately (< 50ms) without triggering external network requests to portals.
2. **Given** a search query for movies that yields zero results in the offline database, **When** the search executes, **Then** the system automatically triggers on-demand live scraping across active movie portals, returns responsive items within timeout budgets, and stores the newly discovered records in the persistent database.
3. **Given** a search query for games or music that yields zero results in the offline database, **When** the search executes, **Then** the system returns an empty result set with appropriate feedback while queuing the search terms for background crawler exploration.
4. **Given** a user navigates to the home page with no search query, **When** viewing the shelves, **Then** trending and latest items for the active category are served dynamically from the local database index.

---

### User Story 2 - AI-Assisted Continuous Background Scraping with LangChain (Priority: P2)

As a system maintainer and media consumer, I want three dedicated, continuously running background workers (one each for movies, games, and music) that scrape portals and use LangChain/LLMs to extract structured links and metadata, so that the offline database remains rich, accurate, and resilient against portal layout changes.

**Why this priority**: Portals frequently alter HTML layouts, obfuscate download selectors, or format multi-part archives in complex tables. Using LangChain with LLMs enables robust extraction of download variants, audio tracks, and archive parts that rigid regexes fail to parse.

**Independent Test**: Can be tested by running the background worker daemon for a category, feeding unstructured portal HTML from an Iranian media site, and verifying that LangChain extracts structured Pydantic models with validated download links, archive passwords, and quality labels into the database.

**Acceptance Scenarios**:

1. **Given** the three background worker processes (movies, games, music), **When** the service is active, **Then** each worker runs independently and perpetually at configured crawl intervals, inspecting upstream portals for new or updated releases.
2. **Given** a crawler encounters a post with complex, non-standard layout (e.g., irregular download tables, embedded passwords, or unstructured text lists), **When** conventional HTML selectors yield incomplete data, **Then** the worker invokes LangChain structured extraction chains to parse the page into typed entity schemas.
3. **Given** LangChain extracts download links and metadata, **When** post-processing runs, **Then** all media URLs undergo scheme and host validation, titles undergo Persian/Arabic NFKC normalization, and records are upserted into the persistent database.
4. **Given** a game post containing multiple archive parts, **When** LangChain extracts the release, **Then** parts are sorted sequentially, missing part numbers are flagged, and the extraction password is isolated into structured storage.

---

### User Story 3 - Source Registry Management & Community Submissions (Priority: P3)

As a platform operator or community contributor, I want to manage active source addresses, disable faulty scrapers, and submit new media portals for review with full authorization, so that the aggregation network stays healthy and expandable without deploying code changes.

**Why this priority**: Scraper portals frequently rotate domains or degrade. Operators need persistent configuration toggles and mirror updates, while users need a functioning submission queue to expand portal coverage toward target quotas.

**Independent Test**: Can be tested by authenticating as an operator, updating a source's primary or fallback address on the Sources screen, reloading the page to confirm persistence, and submitting a new portal suggestion to verify that it is stored in the review queue.

**Acceptance Scenarios**:

1. **Given** an authenticated operator on the Source Registry page, **When** they edit a primary or fallback mirror address for a portal, **Then** the updated address is persisted in the database and applied to all subsequent scrape operations.
2. **Given** an authenticated operator toggles a source between enabled and disabled, **When** the state change is submitted, **Then** the source is immediately updated in the database and included or excluded from live aggregation queries.
3. **Given** a user submits a portal suggestion through the "Suggest a source" form with valid details, **When** they confirm the unauthenticated links policy and submit, **Then** the suggestion is recorded in the operator review queue with its submission count incremented if already suggested.
4. **Given** an unauthenticated request attempts to modify source configuration or triage suggestions, **When** the request reaches the endpoint, **Then** the request is rejected with a 401/403 authorization error.

---

### User Story 4 - Authentic YouTube to MP3 Audio Extraction (Priority: P4)

As a music listener, I want to paste a YouTube video URL and download an extracted, tagged MP3 audio file with transparent progress tracking, so that I can listen to offline music tracks without relying on simulated animations.

**Why this priority**: The dedicated YouTube to MP3 conversion screen currently runs a timer animation that generates mock progress and cannot provide a real audio download. Fulfilling the user promise requires a reliable backend processing queue.

**Independent Test**: Can be tested by submitting a valid public YouTube link, monitoring the progress through discrete status steps, and receiving a valid, playable MP3 file with the selected bitrate streamed directly upon completion with zero permanent server storage.

**Acceptance Scenarios**:

1. **Given** a user submits a valid public YouTube music video URL with chosen bitrate and sample rate, **When** conversion begins, **Then** a background job is created and the user receives verifiable real-time progress updates through completion.
2. **Given** a conversion job successfully completes, **When** the client initiates download, **Then** the audio file is streamed directly as an attachment and deleted immediately from temporary storage with zero permanent retention.
3. **Given** a user submits an unavailable, private, or age-restricted video URL, **When** processing fails, **Then** the job reports a clear, descriptive error state and ceases execution.
4. **Given** a user visits their conversion history, **When** previous conversions exist, **Then** they can review conversion metadata while media files remain un-stored on the server.

---

### User Story 5 - Intelligent Context-Aware Search Assistant (Priority: P5)

As a user searching for specific releases or asking about source health, I want to interact with an AI Assistant powered by an LLM agent with database tools, so that I receive accurate answers about dubbed releases, missing parts, or portal downtime rather than canned responses.

**Why this priority**: The floating assistant currently matches static keywords with hardcoded mock answers. Connecting it to live platform data enables conversational discovery across large catalogs.

**Independent Test**: Can be tested by asking natural-language questions regarding current source status or release availability and verifying that answers cite actual live platform records.

**Acceptance Scenarios**:

1. **Given** a user asks the assistant which sources are degraded or offline, **When** the query is processed, **Then** the assistant queries the live source health table and returns an accurate status breakdown.
2. **Given** a user asks for specific release attributes (such as 1080p dubbed releases or multi-part games), **When** the inquiry is submitted, **Then** the assistant executes catalog search tools and returns matching media cards linking directly to the verified catalog items.
3. **Given** a user maintains an ongoing conversation, **When** subsequent questions refer to previous context, **Then** session context is preserved and utilized for relevant follow-up answers.

---

### User Story 6 - Centralized Adaptive Background Scraping Pipeline (Priority: P2)

Centralized queue needed. For movies, music, games.  Adaptive scraping. Find information. Schedule workers.
As a media seeker and system maintainer, I want a centralized adaptive queue to continuously schedule and manage background scraping workers for each media category (movies, music, games), so that newly published releases and direct links are discovered around the clock without triggering IP bans.

**Why this priority**: Keeps the local indexed database fresh continuously, minimizing the frequency of cache misses and on-demand live crawl triggers.

**Independent Test**: Can be tested independently by running the queue scheduler across multiple configured media portals and verifying that workers execute on an adaptive continuous loop, apply backoff upon receiving rate-limiting signals, and prevent domain over-concurrency.

**Acceptance Scenarios**:

1. **Given** the scraping queue service is running, **When** inspected, **Then** each supported media portal source has scheduled ingestion tasks executing continuously in accordance with domain rate limits.
2. **Given** an on-demand live search task is enqueued by an active user, **When** processed by the centralized queue, **Then** it receives priority execution ahead of regular continuous background crawl passes.
3. **Given** a specific target portal experiences transient HTTP throttling (429 or slow responses), **When** detected, **Then** the centralized queue dynamically increases delay for that domain without halting other source workers.

### Edge Cases

- **Search Cache Invalidation**: When a live scrape occurs or background crawler discovers newer download links for an existing title, the database record must be upserted cleanly without duplicating media items or download variants.
- **Worker Rate Limiting & Cloudflare**: When background crawlers encounter Cloudflare or CAPTCHA challenges, workers must handle exponential backoff, employ solver mechanisms, and never crash the persistent loop.
- **LangChain LLM Failover**: When an LLM structured extraction call fails, times out, or returns unparseable content, the worker must not guess or apply brittle heuristics; it must persist the raw page payload and error details into a dead-letter queue (`extraction_dead_letter`) and proceed to the next item.
- **Concurrent Search & Crawl DB Access**: SQLite database writes from background crawlers and read operations from the web API must utilize WAL mode (`journal_mode=WAL`) and proper busy timeouts to prevent lock contention.
- **YouTube Media Stream Interruption**: If a client disconnects during the immediate MP3 stream download, the temporary audio file must be cleaned up by a guaranteed finally/cleanup hook.


### User Story 7 - Strict AI-Assisted Structured Extraction and DLQ Reliability (Priority: P3)

As a candidate comparing technical requirements and salaries across disparate platforms, I want raw web postings to be analyzed by an AI extraction engine with strict schema enforcement and dead-letter queue resilience, so that job details, tech tags, and dual-currency salaries are accurate and no failed listings are lost.

**Why this priority**: Eliminates brittle regex scraping for complex unstructured descriptions while guaranteeing that transient AI failures do not drop discovered opportunities.

**Independent Test**: Can be tested by processing raw job listings through the AI extraction pipeline and verifying that all valid descriptions produce complete structured schemas, while simulated AI extraction failures correctly land in the Dead Letter Queue for retried execution.

**Acceptance Scenarios**:

1. **Given** an unstructured job description with mixed Persian and English technical requirements, **When** processed by the AI extraction pipeline, **Then** normalized tech stack tokens, standardized company names, and canonical job titles are populated.
2. **Given** an Iranian job description quoting salary in Rial or colloquial Toman, **When** processed, **Then** salary figures are normalized to baseline integer units (with UI-ready Toman representation) alongside USD international indicators.
3. **Given** an AI provider timeout or rate limit during extraction, **When** parsing fails, **Then** the raw job link and payload are routed to the Dead Letter Queue (DLQ) with error metadata for scheduled retry.
4. **Given** a failed extraction in the DLQ, **When** retried after backoff, **Then** it completes extraction and updates the canonical listing without duplicating records.
---

## Requirements *(mandatory)*

### Functional Requirements

#### Search Indexing & Query Execution
- **FR-001**: System MUST index and persist all search results from live scraping into the local SQLite database (`media_items`, `download_variants`, `game_releases`, `game_parts`) with FTS5 search indexing.
- **FR-002**: System MUST serve search queries from the local database index first across all categories.
- **FR-003**: System MUST execute live on-demand scraper queries for the **movies** category ONLY when the local database index returns zero matching items (or when explicit refresh is requested).
- **FR-004**: System MUST serve **games** and **music** search queries strictly from the offline database index populated by background crawlers.
- **FR-005**: System MUST provide dynamic catalog feeds for trending, latest, and featured shelves per media category sourced directly from the database.
- **FR-006**: System MUST support query filtering by quality, codec, audio language, censorship classification, and access tier at the database level.
- **FR-007**: System MUST support pagination parameters (`limit`, `offset`) on search and catalog endpoints.
- **FR-008**: System MUST provide a single-item detail endpoint (`GET /api/items/{id}`) returning complete variant matrices, release parts, and streaming links.

#### AI-Assisted Background Crawling with LangChain
- **FR-009**: System MUST operate three independent, continuous background crawler processes: one for movies, one for games, and one for music.
- **FR-010**: System MUST crawl registered sources periodically according to configurable per-source intervals and page depths.
- **FR-011**: System MUST integrate LangChain structured extraction chains with defined Pydantic output schemas for parsing unstructured portal HTML, connecting to cloud LLM providers configured via environment variables (`LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`).
- **FR-012**: System MUST use LangChain extraction to parse complex download matrices, identifying resolution, codec, file size, audio language (dub vs soft-sub), and censorship flags.
- **FR-013**: System MUST use LangChain extraction to parse multi-part game archives, isolating release group, version, archive password, and individual part download URLs.
- **FR-014**: System MUST validate all extracted download URLs (scheme, host) and perform Persian/Arabic NFKC Unicode normalization on all titles and artist names before database insertion.
- **FR-015**: System MUST log crawl metrics (pages visited, items created, items updated, errors) and persist operational crawl state in `crawl_state`.
- **FR-016**: System MUST persist unparseable, malformed, or failed LLM extraction attempts into an extraction dead-letter queue (`extraction_dead_letter`) with raw HTML and error diagnostics for administrator inspection.

#### Source Registry & Community Submissions
- **FR-017**: System MUST provide real-time source health and configuration records reflecting current connectivity, access tiers, and operational states.
- **FR-018**: System MUST persist runtime updates to portal primary base addresses and fallback mirror addresses in the database.
- **FR-019**: System MUST allow operators to persistently toggle sources between enabled and disabled states.
- **FR-020**: System MUST accept and store user source suggestions including portal URL, category, branding name, default audio track, and optional notes.
- **FR-021**: System MUST deduplicate portal suggestions by root domain and maintain an aggregate submission count.
- **FR-022**: System MUST restrict administrative source updates and suggestion triage behind JWT Bearer token authentication (`Authorization: Bearer <token>`) with role-based operator authorization.

#### Media Utility (YouTube to MP3)
- **FR-023**: System MUST accept valid YouTube video URLs and initiate asynchronous background audio extraction with configurable bitrate and sample rate.
- **FR-024**: System MUST track conversion lifecycle states (queued, processing, completed, failed) with verifiable progress percentage and status descriptions.
- **FR-025**: System MUST stream completed audio files directly to the requesting client as binary MP3 attachments with sanitized filenames and embedded metadata tags.
- **FR-026**: System MUST enforce immediate single-use streaming with zero persistent server-side media retention, purging temporary files immediately after delivery.
- **FR-027**: System MUST enforce an hourly rate limit per client identity to prevent abuse of compute and network resources.

#### Conversational Search Assistant
- **FR-028**: System MUST provide a chat endpoint (`POST /api/chat`) powered by an LLM agent implemented with LangChain.
- **FR-029**: System MUST equip the assistant agent with function tools to query the media catalog, search by specific attributes (resolution, dubbing, missing parts), and inspect live source health.
- **FR-030**: System MUST support multi-turn conversational context within user sessions.

#### Centralized Adaptive Scraping Queue (User Story 6)
- **FR-031**: System MUST implement a centralized asynchronous task queue and scheduler (`CrawlScheduler`) managing crawl and search jobs across all media categories (movies, games, music).
- **FR-032**: System MUST prioritize on-demand live search requests over background periodic crawl passes in the centralized queue.
- **FR-033**: System MUST enforce domain-level concurrency limits (maximum concurrent requests per portal domain) to prevent triggering IP bans or server resource starvation.
- **FR-034**: System MUST apply adaptive exponential backoff to specific domains upon encountering throttling indicators (HTTP 429, 503, connection timeouts) without slowing or halting crawler jobs for unaffected domains.

#### Strict AI-Assisted Structured Extraction and DLQ Reliability (User Story 7)
- **FR-035**: System MUST enforce strict Pydantic schemas via LangChain structured output for all extracted media and portal records, validating types and normalizing technical tags (resolution, codecs, audio dubbing, languages).
- **FR-036**: System MUST capture all failed or timed-out AI extraction attempts into an extraction dead-letter queue table (`extraction_dead_letter`) with raw HTML, error diagnostics, and retry count.
- **FR-037**: System MUST provide an automated DLQ retry mechanism with exponential backoff that re-processes failed extractions and safely upserts results to the canonical database without duplicating records.
- **FR-038**: System MUST provide an administrative endpoint (`GET /api/admin/dlq` and `POST /api/admin/dlq/{id}/retry`) to inspect and manually trigger DLQ item re-processing.

#### Policy & Constitution Governance
- **FR-039**: System MUST strictly adhere to the No Media Relaying principle for general catalog aggregation, ensuring all movie, game, and music download links direct users directly to upstream CDNs.
- **FR-040**: System MUST govern the YouTube to MP3 utility as an explicit, isolated exception to the No Media Relaying principle, operating strictly with immediate single-use streaming and zero persistent server-side media retention.
- **FR-041**: Scraper plugins and background crawler modules MUST remain decoupled, with zero cross-scraper imports.
- **FR-042**: SQLite operations MUST use WAL mode and connection pooling to ensure safe concurrent access between API handlers and background crawler workers.

---

### Key Entities

- **MediaItem**: Central catalog record representing a movie, series, game, or music release, containing normalized titles, release year, poster art, descriptions, rating, censorship classification, and associated download/part variants.
- **DownloadVariant**: Specific playable or downloadable file for a movie or music release, characterized by resolution, codec, audio language, file size, access tier, and upstream CDN URL.
- **GameRelease**: Structured package of one or more multi-part archives for a game title, including release group, total unpacked size, extraction password, and sequential part links with gap tracking.
- **CrawlWorker**: Dedicated background daemon process assigned to a specific media category (`movies`, `games`, `music`), managing crawl schedules, page fetching, and rate limiting.
- **ExtractionSchema**: LangChain structured Pydantic schema used by LLMs to parse unstructured portal HTML into typed media records, download variants, and part links.
- **AdaptiveCrawlQueue**: Centralized asynchronous task queue managing priority levels (live user search > background crawl) and scheduling crawl jobs across categories.
- **DomainThrottlePolicy**: Rate limiting and backoff profile per target portal domain, tracking active concurrency, request delay, backoff multiplier, and consecutive failure counts.
- **DeadLetterQueueItem**: Record of a failed or timed-out AI extraction in `extraction_dead_letter`, tracking source ID, page URL, raw HTML, error diagnostic, retry count, and resolution state.
- **SourcePortal**: Configuration and health profile of an upstream indexing scraper, tracking base and mirror URLs, category coverage, active reachability state, failure counts, and access tier.
- **SourceSuggestion**: Community-submitted portal candidate awaiting operator review, containing target URL, normalized domain, category, proposed tier, submission count, and verification status.
- **AudioConversionJob**: Asynchronous task for extracting YouTube audio, tracking source video ID, title, target audio specifications, current processing stage, and stream delivery state.
- **AssistantSession**: Contextual state for user interactions with the search assistant, preserving query history, referenced catalog entities, and active filters.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Repeat or indexed search queries resolve and return complete result sets in under 50 milliseconds across all categories.
- **SC-002**: 100% of on-demand live movie search results are indexed and stored in the persistent database upon retrieval.
- **SC-003**: Background crawlers for movies, games, and music maintain 99.5% daemon uptime, continuously indexing new releases across registered sources.
- **SC-004**: LangChain AI-assisted extraction achieves over 95% accuracy in parsing non-standard download tables, archive passwords, and quality labels where conventional regex fails.
- **SC-005**: 100% of home page shelves (trending, latest) are dynamically populated from live catalog records without static fixture dependencies.
- **SC-006**: 100% of multi-part game releases with missing sequential parts accurately identify the exact missing part numbers to the user before download.
- **SC-007**: Source configuration modifications (address changes, enable/disable toggles) persist across service restarts with 100% reliability.
- **SC-008**: 100% of valid source suggestions submitted via the user interface are successfully recorded in the review queue and deduplicated by domain.
- **SC-009**: Converted YouTube audio files are streamed directly upon completion with zero residual media files persisting on the server disk.
- **SC-010**: Zero media payloads for movies, series, or games are buffered or proxied through the application server, maintaining full compliance with the core direct-link aggregation principle.
- **SC-011**: On-demand live search requests preempt background crawl tasks in the centralized queue within 100 milliseconds.
- **SC-012**: Domain-level adaptive backoff automatically throttles degrading portals without increasing response latency or task execution times for healthy portals.
- **SC-013**: 100% of failed AI extractions are preserved in the DLQ with zero dropped listings, and subsequent retries cleanly upsert into the database with zero duplicate records.

---

## Assumptions

- Target users browse through standard modern desktop and mobile web browsers with native audio/video playback capabilities.
- Upstream media portals provide publicly reachable HTTP/HTTPS direct download links without requiring user authentication or paywall bypass.
- The hosting environment for the backend service possesses sufficient temporary disk space, compute capacity, and outbound bandwidth for background crawling and on-the-fly audio extraction.
- An LLM API key (e.g., Anthropic, OpenAI, or compatible local/proxy endpoint) is configured in environment variables to support LangChain extraction chains and the conversational assistant.
- SQLite in WAL mode with appropriate busy timeouts is sufficient to support concurrent reads from the FastAPI server and writes from the three background category workers.
