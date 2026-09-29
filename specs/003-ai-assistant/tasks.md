# Tasks: AI Conversational Search Assistant

**Input**: Design documents from `/specs/003-ai-assistant/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/chat-api.yaml`, `quickstart.md`
**Tests**: Included per Constitution Principle IV (Testability & Offline Verification) and feature specification requirements.
**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`, `[US4]`, `[US5]`)
- Exact file paths included in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Assistant package initialization and environment configuration

- [ ] T001 Initialize assistant subsystem package in `apps/api/assistant/__init__.py` and configure environment variables (`AI_API_BASE_URL`, `AI_MODEL`, `AI_API_KEY`, `AI_TIMEOUT`)
- [ ] T002 [P] Create mock response fixtures and helper functions for offline LLM and web search testing in `apps/api/tests/fixtures/assistant/mock_responses.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core agent models, tool schemas, agent loop, and API routing that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 [P] Define chat data models (`ChatMessage`, `ChatRequest`, `ChatResponse`, `ToolExecutionEvent`) and tool schemas (`SEARCH_CATALOG_TOOL`, `SEARCH_WEB_TOOL`) in `apps/api/assistant/models.py`
- [ ] T004 [P] Implement core asynchronous tool-calling agent loop using `httpx.AsyncClient` against OpenAI-compatible chat completions in `apps/api/assistant/agent.py`
- [ ] T005 Implement catalog search tool adapter `search_catalog(category, query)` interfacing with `db.search()` and `web.app.search_media` in `apps/api/assistant/tools.py`
- [ ] T006 Setup API routes `POST /api/chat` (supporting JSON and SSE streaming) and `GET /api/chat/session/{session_id}` in `apps/api/web/app.py`

**Checkpoint**: Foundation ready - assistant backend can receive messages, invoke local search tool, and return responses.

---

## Phase 3: User Story 1 - Conversational Discovery via Dockable Web Chat Widget (Priority: P1) 🎯 MVP

**Goal**: A visitor browsing any page can open a floating chat widget, converse in Persian or English describing what they want, and receive formatted media cards with direct download links.

**Independent Test**: Load the web app in browser, open the widget, enter a natural language media query (e.g. "Suggest a mind-bending sci-fi movie"), verify that the assistant translates the prompt, queries the local catalog, and renders media cards with direct CDN download links.

### Tests for User Story 1

- [ ] T007 [P] [US1] Add unit and contract tests for `/api/chat` endpoint and SSE stream events in `apps/api/tests/test_assistant.py`

### Implementation for User Story 1

- [ ] T008 [P] [US1] Create Jinja2 chat widget template partial with floating trigger bubble, collapsible window, header, messages container, and prompt input in `apps/api/web/templates/_chat_widget.html`
- [ ] T009 [P] [US1] Create chat widget styling supporting dark/gold theme, responsive mobile positioning, smooth transitions, and RTL layout in `apps/api/web/static/chat_widget.css`
- [ ] T010 [US1] Implement vanilla ES6 chat widget client handling `sessionStorage`, SSE event stream decoding, message rendering, and media card formatting in `apps/api/web/static/chat_widget.js`
- [ ] T011 [US1] Include `_chat_widget.html`, `chat_widget.css`, and `chat_widget.js` in `apps/api/web/templates/base.html`

**Checkpoint**: User Story 1 is fully functional as an MVP. Users can chat via web widget and receive catalog recommendations with direct links.

---

## Phase 4: User Story 2 - Natural Language Translation to Multi-Term Catalog Queries (Priority: P1)

**Goal**: Assistant translates vague memories, plot descriptions, and phonetic Persian transliterations into canonical search terms across movies, series, games, and music.

**Independent Test**: Submit a vague plot description ("movie where Leonardo DiCaprio is in people's dreams") or Persian transliteration ("اینسپشن"), verify the assistant extracts the canonical title ("Inception"), formulates multi-term queries, and returns accurate catalog items.

### Tests for User Story 2

- [ ] T012 [P] [US2] Add unit tests for natural language intent extraction and Persian/English query translation in `apps/api/tests/test_assistant.py`

### Implementation for User Story 2

- [ ] T013 [US2] Implement system prompt instructions and query formulation logic in `apps/api/assistant/agent.py` to extract media category, primary title, candidate search query strings in English and Persian, and quality attributes
- [ ] T014 [US2] Enhance `search_catalog` in `apps/api/assistant/tools.py` to execute queries across candidate translations and rank matched items by relevance

**Checkpoint**: User Stories 1 and 2 work together. Assistant handles colloquial and transliterated queries accurately.

---

## Phase 5: User Story 3 - Strict Tool Hierarchy: Local Catalog First, Web Search Fallback (Priority: P2)

**Goal**: Enforce strict tool execution hierarchy: assistant queries local catalog first; only when catalog returns zero results does it autonomously trigger the external web search tool and report live progress to the user.

**Independent Test**: Search for a known title (verify only catalog tool is invoked). Then search for an unindexed title (verify local catalog returns 0, status event "Searching external media sources..." appears, and web search tool is executed).

### Tests for User Story 3

- [ ] T015 [P] [US3] Add unit tests for sequential tool hierarchy and conditional web search fallback in `apps/api/tests/test_assistant.py`

### Implementation for User Story 3

- [ ] T016 [US3] Implement `search_web(query, category)` fallback tool in `apps/api/assistant/web_search.py` using `httpx` and `selectolax` to query public web search, parse candidate media landing pages, and extract direct CDN download links
- [ ] T017 [US3] Enforce strict tool execution gate in `apps/api/assistant/agent.py` ensuring `search_web` is strictly disallowed until `search_catalog` has completed and returned 0 results
- [ ] T018 [US3] Stream real-time status events (`Searching catalog...`, `Searching external media sources...`, `No results found`) through `/api/chat` SSE stream in `apps/api/web/app.py` and update the widget status badge in `apps/api/web/static/chat_widget.js`

**Checkpoint**: User Stories 1, 2, and 3 work together. Assistant falls back to web search only when local catalog has no matches.

---

## Phase 6: User Story 4 - Autonomous Catalog Ingestion & Permanent Indexing (Priority: P2)

**Goal**: Discovered external media items and direct download links are automatically validated, deduplicated, and ingested into the SQLite FTS5 database, making future searches resolve from local catalog in <1s.

**Independent Test**: Perform an external web fallback search for Title X, verify Title X is upserted into `data/index.db`, then run a second search for Title X and confirm it resolves from local catalog without invoking web search.

### Tests for User Story 4

- [ ] T019 [P] [US4] Add tests for external item ingestion, SQLite FTS5 indexing, and subsequent local retrieval in `apps/api/tests/test_assistant.py`

### Implementation for User Story 4

- [ ] T020 [US4] Implement `index_discovered_media(items)` in `apps/api/assistant/tools.py` mapping web discovery results to `MediaItem` models, validating direct CDN links (Constitution Principle III), filtering duplicates, and committing via `db.upsert_items()`
- [ ] T021 [US4] Integrate automatic post-discovery ingestion in `apps/api/assistant/agent.py` to trigger `index_discovered_media` asynchronously when `search_web` returns valid results

**Checkpoint**: Catalog self-enriches from web search. Newly discovered items become immediately discoverable in local catalog searches.

---

## Phase 7: User Story 5 - Multi-Turn Contextual Refinement & Cross-Media Pivoting (Priority: P3)

**Goal**: User converses iteratively to narrow down results (e.g., "only 1080p dubbed", "give me the soundtrack"), with the assistant maintaining session memory across turns.

**Independent Test**: Conduct a 3-turn conversation starting from a broad movie search, adding a quality filter, and requesting related soundtrack or game media; verify all turns maintain contextual continuity.

### Tests for User Story 5

- [ ] T022 [P] [US5] Add tests for multi-turn session history retention and contextual query refinement in `apps/api/tests/test_assistant.py`

### Implementation for User Story 5

- [ ] T023 [US5] Implement session memory manager in `apps/api/assistant/agent.py` maintaining in-memory sliding window history (up to 10 turns) per session ID, with endpoint `DELETE /api/chat/session/{session_id}` in `apps/api/web/app.py`
- [ ] T024 [US5] Add "New Chat" reset action and active filter badge indicators in `apps/api/web/static/chat_widget.js` and `apps/api/web/templates/_chat_widget.html`

**Checkpoint**: Assistant supports seamless multi-turn conversations and contextual refinement.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Security hardening, compliance auditing, and end-to-end verification

- [ ] T025 [P] Audit all extracted and generated links in `apps/api/assistant/web_search.py` and `apps/api/assistant/tools.py` to ensure 100% compliance with Constitution Principle III (direct CDN URLs only, zero media relay)
- [ ] T026 [P] Implement prompt injection defense, non-media query guardrails, and message length validation in `apps/api/assistant/agent.py`
- [ ] T027 Execute all verification scenarios in `specs/003-ai-assistant/quickstart.md` and run full test suite with `pytest tests` to verify zero regressions

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3 - P1)**: Depends on Foundational phase - delivers working MVP
- **User Story 2 (Phase 4 - P1)**: Depends on US1 completion - enhances query translation
- **User Story 3 (Phase 5 - P2)**: Depends on US2 completion - adds web search fallback
- **User Story 4 (Phase 6 - P2)**: Depends on US3 completion - adds automatic indexing of web results
- **User Story 5 (Phase 7 - P3)**: Depends on US1 completion - adds multi-turn context
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

```text
Foundational (Phase 2)
  │
  ▼
User Story 1 (P1: Web Chat Widget MVP) ───► User Story 5 (P3: Multi-Turn Context)
  │
  ▼
User Story 2 (P1: Query Translation)
  │
  ▼
User Story 3 (P2: Web Search Fallback)
  │
  ▼
User Story 4 (P2: Auto-Indexing & Catalog Enrichment)
  │
  ▼
Polish & Hardening (Phase 8)
```

### Parallel Opportunities

- **Phase 1**: T001 and T002 can run in parallel
- **Phase 2**: T003 and T004 can run in parallel
- **Phase 3 (US1)**: T007 (tests), T008 (HTML partial), and T009 (CSS) can run in parallel
- **Phase 5 (US3)**: T015 (tests) and T016 (web scraper) can run in parallel
- **Phase 6 (US4)**: T019 (tests) and T020 (ingestion adapter) can run in parallel
- **Phase 8**: T025 and T026 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch tests and frontend assets concurrently:
Task: "T007 [P] [US1] Add unit and contract tests for /api/chat in apps/api/tests/test_assistant.py"
Task: "T008 [P] [US1] Create Jinja2 chat widget partial in apps/api/web/templates/_chat_widget.html"
Task: "T009 [P] [US1] Create chat widget styling in apps/api/web/static/chat_widget.css"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`T001`, `T002`)
2. Complete Phase 2: Foundational (`T003`, `T004`, `T005`, `T006`)
3. Complete Phase 3: User Story 1 (`T007`, `T008`, `T009`, `T010`, `T011`)
4. **STOP and VALIDATE**: Verify chat widget opens and queries local catalog in browser
5. Deliver functional MVP increment

### Incremental Delivery

1. Complete Setup + Foundational → Backend ready for assistant requests
2. Add User Story 1 → Web chat widget with local catalog search (MVP!)
3. Add User Story 2 → Smarter natural language and Persian transliteration matching
4. Add User Story 3 → Autonomous web search fallback when catalog has 0 hits
5. Add User Story 4 → Automatic ingestion and indexing of discovered web media
6. Add User Story 5 → Multi-turn refinement and conversation resets
7. Run Polish phase → Constitution compliance audit, guardrails, and full test suite
