# Feature Specification: AI Conversational Search Assistant

**Feature Branch**: `003-ai-assistant`

**Created**: 2026-09-29

**Status**: Draft

**Input**: User description: "i need a ai assistant (chatbot) that the user can interact with in order to find the movies he or she likes, the ai then should translate the user inputs to different search terms and use the currently developed engine for finding the movies/games/music the user is looking for, if not found any result fallback to ai-web-search tool (which its result should be stored and indexed for later findings and user searches), the ai-assistant should be accessable via a widget in the web interface. the AI initially should only be able to use the existing developed search engine with python in this codebase (use the engine as tools) then fallback to web-search in case of no results. slug=ai-assistant"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conversational Discovery via Dockable Web Chat Widget (Priority: P1)

A user navigating the media aggregator wants to open a floating, non-intrusive chat widget from any page, converse in natural language (Persian or English) describing what they want to watch, play, or listen to, and receive curated media recommendations with direct download links without needing to know exact keywords or browse multiple categories.

**Why this priority**: Core user touchpoint. Transforms standard keyword search into an intelligent, guided discovery journey accessible across the entire web application.

**Independent Test**: Can be tested by loading any web page, clicking the widget bubble to expand the chat interface, submitting a natural language prompt (e.g., "Suggest a mind-bending sci-fi movie from the 2010s" or "یک فیلم کمدی خانوادگی جدید معرفی کن"), and verifying that the assistant interprets the request, queries the local catalog, and renders interactive media cards with direct download links.

**Acceptance Scenarios**:

1. **Given** a visitor browsing any page of the web application, **When** they click the chat bubble in the bottom corner, **Then** a responsive chat widget expands with an active input field, suggested starter prompts, and current session history.
2. **Given** an open chat widget, **When** the user submits a natural language request, **Then** the interface displays an immediate processing indicator, and the assistant streams or delivers a contextual response accompanied by relevant media result cards.
3. **Given** media results returned by the assistant, **When** displayed in the conversation stream, **Then** each item presents title (Persian and English where available), category badge (Movie, Series, Game, Music), release year/quality tags, and clickable direct CDN download links.
4. **Given** a user navigating between different pages of the website, **When** navigating or reopening the widget, **Then** the ongoing conversation state, message history, and widget open/closed preference are preserved without page refresh resets.

---

### User Story 2 - Natural Language Translation to Multi-Term Catalog Queries (Priority: P1)

A user describes their media preference using vague memories, colloquial descriptions, plot summaries, or actors ("the movie where Leonardo DiCaprio is in people's dreams", "بازی اکشن جهان‌باز مثل جی تی ای"), and the assistant extracts the underlying intent, identifies the target media titles and categories, translates the prompt into candidate search terms, and queries the local search engine.

**Why this priority**: Bridges the gap between how humans remember media and how database indexes match records. Handles transliteration between Persian and English seamlessly.

**Independent Test**: Can be tested by entering vague plot descriptions or phonetic Persian transliterations of foreign titles, verifying that the assistant resolves the canonical title, formulates targeted search terms, executes local search, and presents the correct matched title.

**Acceptance Scenarios**:

1. **Given** a vague or plot-based user query, **When** the assistant processes the input, **Then** it identifies candidate canonical titles, media categories, and attributes (director, actor, year, genre).
2. **Given** a foreign title expressed in Persian script (e.g., "اوپنهایمر" or "اینسپشن"), **When** the assistant translates the query, **Then** it produces both normalized Persian and original English search queries to maximize local index hit rates.
3. **Given** candidate search queries, **When** searching the local catalog, **Then** the assistant executes searches scoped to the identified media category (Movies/Series, Games, or Music) to avoid irrelevant cross-category noise.
4. **Given** multiple plausible interpretations of a user prompt, **When** the catalog contains matches for several candidate titles, **Then** the assistant presents the top candidates clearly categorized and asks the user which one they intended.

---

### User Story 3 - Strict Tool Hierarchy: Local Catalog First, Web Search Fallback (Priority: P2)

When a user searches for rare, niche, or newly released media not yet present in the local catalog, the assistant first exhausts local catalog queries; only upon confirming zero matching results does it autonomously escalate to an external web search discovery tool to find working direct download links.

**Why this priority**: Guarantees fast, cost-efficient, and offline-capable search first, while ensuring users never hit dead ends when the internal catalog lacks an item.

**Independent Test**: Can be tested by searching for a title known to exist locally (verifying only local catalog tools are invoked), and then searching for an unindexed release (verifying local search returns zero, followed by an explicit status notice and invocation of the web discovery tool).

**Acceptance Scenarios**:

1. **Given** a user request whose target exists in the local catalog, **When** the assistant searches, **Then** it uses only the local catalog tool and returns results without invoking external web search.
2. **Given** a search where all local catalog query variants return zero results, **When** the assistant confirms the absence of local matches, **Then** it posts a real-time progress update (e.g., "Searching external media sources...") and invokes the external web search tool.
3. **Given** external web search execution, **When** the tool discovers source pages, **Then** it extracts verified direct download links, quality variants, and metadata, returning them to the assistant for presentation to the user.
4. **Given** an external search that fails to locate direct links, **When** discovery concludes, **Then** the assistant clearly explains that no direct links could be located across all sources and suggests related available titles or refined search terms.

---

### User Story 4 - Autonomous Catalog Ingestion & Permanent Indexing (Priority: P2)

When external web search successfully discovers new media titles and direct links, the system automatically validates, formats, and persists the discovered entries into the central search index, making those items permanently and immediately available for all future user searches.

**Why this priority**: Transforms the platform into a self-enriching media index. Every search query that triggers external discovery enriches the shared catalog for the entire community, permanently reducing future external search overhead.

**Independent Test**: Can be tested by performing an external fallback search for Title X, verifying that Title X is ingested into the database, and then immediately performing a standard search for Title X (via regular search bar or assistant) to confirm it is served locally in under 1 second without triggering external web search.

**Acceptance Scenarios**:

1. **Given** successful web search discovery of new media items, **When** the assistant prepares the user response, **Then** the system automatically triggers background ingestion to validate and store the metadata and direct links into the persistent search index.
2. **Given** new entries being ingested, **When** links are checked, **Then** the system discards duplicate links, normalizes titles, assigns proper media categories, and verifies that links conform to direct CDN download standards (never buffering or relaying media).
3. **Given** an item ingested into the catalog from a previous web discovery, **When** any user subsequently searches for that item, **Then** the system serves the record directly from the local catalog without triggering external web tools.

---

### User Story 5 - Multi-Turn Contextual Refinement & Cross-Media Pivoting (Priority: P3)

A user wants to converse back and forth with the assistant to narrow down search results by specific criteria (e.g., "only show 1080p with Persian dubbing", "which one has the smallest file size?", "now find me the soundtrack for this movie"), maintaining conversation memory across multiple conversational turns.

**Why this priority**: Real-world search is iterative. Users rarely specify all preferences in their first prompt.

**Independent Test**: Can be tested by conducting a 4-turn conversation starting from a broad topic, adding quality constraints, requesting related soundtrack or game media, and verifying that each turn respects the accumulated context.

**Acceptance Scenarios**:

1. **Given** prior media cards presented in the chat, **When** the user replies with a filtering constraint (e.g., "only 1080p versions with Persian dubbing"), **Then** the assistant applies the filter to the existing results without restarting the search from scratch.
2. **Given** an ongoing conversation about a specific movie, **When** the user asks for related media (e.g., "is there a game based on this?" or "give me the soundtrack"), **Then** the assistant recognizes the parent entity, pivots to the requested category (Games or Music), and searches for the corresponding assets.
3. **Given** a user wishing to start a completely new exploration, **When** they click "New Chat" or explicitly declare a topic reset, **Then** the assistant clears conversational context and confirms readiness for a new topic.

---

### Edge Cases

- **Ambiguous or Vague Prompts**: If the user submits extremely broad or underspecified queries ("a movie with cars"), the assistant proposes 2-3 specific popular candidate interpretations or asks a single targeted clarifying question rather than executing dozens of unfocused searches.
- **External Web Search Returns Non-Direct Links**: If web search finds forum discussions, review pages, or landing pages without actionable direct download links, the system filters them out. Only validated direct media links are presented to the user or ingested into the catalog.
- **Upstream Network Latency or Tool Failure**: If the external web search tool times out or fails due to network issues, the assistant gracefully alerts the user, explains the issue without technical jargon, and provides best-effort local suggestions.
- **Mixed Persian/English Queries and Typographical Variations**: Handles character normalization (e.g., Persian vs. Arabic kaf/yeh, half-spaces, common spelling typos) during both intent parsing and query generation.
- **Off-Topic or Adversarial Queries**: If a user asks questions unrelated to finding movies, series, games, or music (e.g., general world knowledge, coding questions, prompt injection attempts), the assistant politely declines and steers the user back to media discovery.
- **Rapid Successive Messages**: If a user sends multiple messages in rapid succession before previous searches complete, the assistant cancels or updates in-flight queries to reflect the latest user instruction, avoiding race conditions in the UI stream.
- **High Volume Duplicate Ingestion**: If multiple users concurrently trigger external search for the same unindexed title, the ingestion pipeline handles concurrency safely using idempotency checks, ensuring no duplicate catalog entries or index corruption.

## Requirements *(mandatory)*

### Functional Requirements

#### Widget & Conversational Interface
- **FR-001**: System MUST provide a persistent floating action button and dockable chat widget accessible across all views of the web application.
- **FR-002**: System MUST allow users to expand, minimize, and reset the chat widget without interrupting current page navigation or media playback.
- **FR-003**: System MUST accept natural language inputs in both Persian and English, including mixed-language queries.
- **FR-004**: System MUST display real-time status indicators in the chat stream during tool execution (e.g., "Searching catalog...", "Consulting external sources...", "Indexing new releases...").
- **FR-005**: System MUST render media search results as structured, high-contrast interactive cards displaying localized titles, media category badges, resolution/quality indicators, audio language flags, and one-click direct download links.

#### Intent Understanding & Query Translation
- **FR-006**: System MUST parse natural language user messages to extract media category (Movie, Series, Game, Music), target title candidates, genres, release years, quality requirements, and language preferences.
- **FR-007**: System MUST translate extracted intents into multiple normalized search query strings (including Persian transliterations and original English titles) optimized for catalog matching.
- **FR-008**: System MUST maintain multi-turn conversational context within an active session to allow iterative query refinement and cross-media pivoting.

#### Tool Execution Hierarchy & Fallback Policy
- **FR-009**: System MUST enforce a strict tool execution hierarchy: the local catalog search tool MUST be invoked first; the external web search tool MUST NOT be called unless local search results are completely empty or confirmed irrelevant.
- **FR-010**: System MUST execute local catalog searches across all generated query variations before concluding that local results are zero.
- **FR-011**: System MUST autonomously invoke the external web search tool upon confirming zero local catalog matches without requiring manual user escalation.
- **FR-012**: System MUST validate that external web search results contain direct, actionable download links conforming to direct media delivery standards before presenting them to the user.

#### Indexing & Catalog Enrichment Pipeline
- **FR-013**: System MUST automatically ingest validated media metadata and direct links discovered via external web search into the central searchable index.
- **FR-014**: System MUST perform title normalization, category assignment, and duplicate link detection prior to committing new records to the catalog.
- **FR-015**: System MUST ensure newly ingested records become immediately searchable and discoverable by both standard search and the conversational assistant within 1 second of persistence.

#### Architectural & Governance Constraints (Constitution Compliance)
- **FR-016**: System MUST strictly adhere to Constitution Principle III: all media links presented or stored MUST be direct client-to-CDN download links; under no circumstances may the server buffer, relay, proxy, or stream media payloads through its own network interface.
- **FR-017**: System MUST encapsulate search tools as decoupled, isolated interfaces adhering to Constitution Principle I.
- **FR-018**: System MUST provide deterministic offline testability with mocked tool fixtures for both catalog search and external web discovery tools adhering to Constitution Principle IV.
- **FR-019**: System MUST keep the client widget lightweight using vanilla web technologies without requiring a heavyweight client-side framework pipeline (Constitution Principle II).
- **FR-020**: System MUST reject and sanitize malicious inputs, prompt injection attempts, and non-media queries, maintaining strict domain focus on media aggregation.

### Key Entities

- **Chat Session**: Represents the active conversational container for a user; holds session identifier, timestamp, active topic/entity, and ordered message history.
- **Chat Message**: An atomic message event in the conversation; attributes include message ID, sender role (user, assistant, system notification), content payload (text or media card bundle), timestamp, and associated tool activity logs.
- **Query Translation Set**: The structured entity produced by intent extraction; includes recognized media category, primary title, candidate search query strings in English and Persian, and attribute filters (resolution, audio dubbing, year).
- **Media Result Card**: The structured presentation object sent to the UI; includes title, canonical English/Persian names, category tag, release year, poster/thumbnail URL, source provider name, and an array of download link options.
- **Download Link Option**: An individual downloadable variant; attributes include direct CDN URL, file size, quality/resolution label (e.g., 1080p, 720p, 320kbps), codec (e.g., x265, x264), and audio track specification (e.g., Persian Dubbed, Original Audio, Soft Subtitle).
- **Web Discovery Record**: Temporary structured payload from external web search containing source URL, page title, extracted candidate media metadata, and raw discovered links awaiting validation and ingestion.
- **Catalog Index Record**: The permanent searchable database entity; contains normalized title, category, metadata attributes, full-text search indexing vectors, and associated direct download URLs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For queries available in the local catalog, the assistant delivers relevant recommendations and direct links to the user in under 3.0 seconds for 90% of requests.
- **SC-002**: For queries requiring external web fallback, the assistant autonomously triggers web discovery and delivers verified direct links in under 8.0 seconds for 85% of fallback requests.
- **SC-003**: 100% of validated media items discovered through external web search are saved and indexed into the local catalog upon retrieval.
- **SC-004**: Subsequent searches (via either the chat widget or the standard search bar) for previously discovered external items resolve from the local catalog in under 0.8 seconds without triggering external web search.
- **SC-005**: 85% of users who interact with the assistant to locate media click or copy a direct download link within 3 conversational turns.
- **SC-006**: The web chat widget opens, initializes, and becomes ready for user input in under 150 milliseconds from user click.
- **SC-007**: 0% of media payloads are relayed or buffered through the application server; 100% of download actions connect the user client directly to upstream CDNs.
- **SC-008**: Intent translation achieves at least 90% accuracy in correctly identifying target titles and categories from conversational prompts in Persian and English.
- **SC-009**: The conversational assistant handles upstream search and tool failures gracefully, with 0% unhandled client exceptions or widget freezes during network faults.

## Assumptions

- Natural language processing and query translation are powered by an integrated conversational model with support for structured tool/function invocation.
- The existing media search engine is exposed internally as a callable tool interface that accepts category and query parameters and returns structured media models.
- The external web discovery tool has programmatic access to search the web, scrape candidate landing pages, and extract direct download links.
- The local catalog database supports immediate upsert/indexing of newly discovered items, making them instantly available to full-text search.
- Widget conversational history is maintained ephemerally in client session storage and server memory for the duration of the visit, requiring no permanent user accounts or authentication.
- Direct links obtained from external sources point directly to publicly accessible upstream CDNs or web distribution servers.
- The chat widget is rendered with lightweight vanilla CSS and JavaScript directly integrated into existing server-rendered HTML templates.
