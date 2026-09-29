# Research & Architecture Decisions: AI Conversational Search Assistant

**Feature**: `003-ai-assistant`
**Date**: 2026-09-29
**Status**: Completed

## 1. LLM Client & Tool-Use Architecture

### Decision
Implement a lightweight, native tool-calling agent loop in `assistant/agent.py` using `httpx.AsyncClient` against an OpenAI-compatible chat completions endpoint (`/v1/chat/completions`).

### Rationale
- **The Ladder / YAGNI**: No heavyweight frameworks (LangChain, LlamaIndex, CrewAI) required. The application already depends on `httpx>=0.27.0`.
- **Standard Protocol**: OpenAI-compatible JSON schema tool-calling (`tools` with `type: "function"` and `tool_calls`) is supported universally by local models (vLLM, Ollama, LM Studio) and remote providers (OpenAI, Groq, Mistral, OpenRouter, DeepSeek).
- **Configuration via Environment Variables**:
  - `AI_API_BASE_URL`: Defaults to `http://localhost:11434/v1` (Ollama default) or remote proxy.
  - `AI_API_KEY`: Defaults to empty or `"dummy"` for local providers.
  - `AI_MODEL`: Defaults to a capable tool-calling model (e.g., `qwen2.5:7b`, `llama3.1:8b`, or remote `gpt-4o-mini` / `claude-3-5-haiku`).
  - `AI_TIMEOUT`: Default 15.0 seconds.

### Alternatives Considered
- **LangChain / LlamaIndex**: Adds 50+ dependencies, complex abstractions, unpredictable prompt overhead, and breaks Constitution Principle II (Simplicity). Rejected.
- **Provider-specific SDKs (e.g. `anthropic`, `openai`)**: Adds multiple SDK dependencies. An OpenAI-compatible REST wrapper over `httpx` works for all providers with zero new packages.

---

## 2. Tool Hierarchy & Fallback Policy

### Decision
Expose two distinct, sequentially staged tools to the assistant:
1. `search_catalog(category, query)`: Queries local SQLite FTS5 index (`db.search`) and actively scrapes sources (`web.app.search_media` pipeline) across movies, series, games, and music.
2. `search_web(query, category)`: Scrapes public web search engines (DuckDuckGo HTML / SearXNG / configurable web search API), parses target media landing pages with `selectolax`, and extracts direct download links.
3. `index_discovered_media(items)`: Automatically invoked when `search_web` finds valid items to commit them into `db.upsert_items()`.

**Enforcement Policy**:
The system prompt and execution controller enforce that `search_catalog` MUST be called first. The agent prompt instructs:
- *"Always search the internal catalog first using candidate Persian and English query terms."*
- *"Only invoke `search_web` if `search_catalog` returns 0 results or explicitly lacks the requested media."*

### Rationale
- Meets user's exact specification: *"the AI initially should only be able to use the existing developed search engine with python in this codebase (use the engine as tools) then fallback to web-search in case of no results."*
- Conserves external network bandwidth and API tokens by prioritizing local SQLite FTS and existing site scrapers.

### Alternatives Considered
- **Parallel catalog + web search**: Wastes resources and slows down responses when items already exist locally. Rejected.
- **Single monolithic search tool**: Hides the fallback boundary from the user and makes real-time status reporting impossible. Rejected.

---

## 3. Web Search & Media Extraction Pipeline

### Decision
Implement `assistant/web_search.py` using `httpx` to search public search endpoints (DuckDuckGo HTML / configurable search endpoint) and scrape result pages using `selectolax` (already in `pyproject.toml`).
- Filter for common media distribution platforms and file download patterns (`.mp4`, `.mkv`, `.mp3`, `.zip`, `.rar`, CDN download links).
- Extract title, poster, file size, quality tags, and direct CDN links.
- Strictly validate links against Constitution Principle III (direct CDN URLs only, no streaming relay).
- Persist discovered items into `data/index.db` via `db.upsert_items()`.

### Rationale
- Zero new dependencies: uses `httpx` and `selectolax` already present in `apps/api`.
- Immediate persistence enriches the central FTS5 index so subsequent searches for that item resolve in <1 second locally without external search.

### Alternatives Considered
- **Headless Browser (Playwright / Selenium)**: Heavyweight (hundreds of MBs of browser binaries), high RAM consumption, breaks Constitution Principle II. Rejected.
- **Paid API (Google Custom Search, Serper)**: Can be supported as an optional override via `AI_WEB_SEARCH_API_KEY`, but zero-dependency DuckDuckGo HTML scraping provides a working default.

---

## 4. Web Widget UI & Real-Time Streaming

### Decision
Implement the chat widget as a lightweight vanilla HTML/CSS/JavaScript component:
- **Template**: `apps/api/web/templates/_chat_widget.html` included inside `base.html`.
- **Styling**: `apps/api/web/static/chat_widget.css` matching the dark/gold theme of the platform.
- **Logic**: `apps/api/web/static/chat_widget.js` (vanilla ES6, <300 lines).
- **Transport**: Server-Sent Events (SSE) via `POST /api/chat` with `text/event-stream` using `EventSource` / `fetch` streaming reader.
- **Session State**: Session ID stored in browser `sessionStorage`; server maintains in-memory sliding window history (last 10 turns per session).

### Rationale
- Complies strictly with Constitution Principle II: Server-rendered HTML with Jinja2 and vanilla modern CSS/JS. No npm build steps, no React/Vue bundle overhead.
- Streaming provides immediate feedback: users see "Searching catalog...", "Searching web...", and text tokens stream in real-time.

### Alternatives Considered
- **WebSocket**: Over-engineered for request-reply conversational search; requires extra connection management and state handling compared to standard HTTP POST + SSE streaming.
- **Polling / Pure JSON**: No live token or tool execution feedback; user would wait 3-8 seconds with a generic spinner. Rejected.

---

## 5. Constitution & Governance Review

| Principle | Status | Evaluation |
|-----------|--------|------------|
| **I. Library / Module Isolation** | PASS | All assistant code isolated in `apps/api/assistant/`. Interacts with `db.py` and `sources/` via public functions. |
| **II. Simplicity / YAGNI** | PASS | No new dependencies. Uses `httpx`, `selectolax`, `sqlite3`, `fastapi`, vanilla HTML/JS/CSS. |
| **III. No Media Relaying (NON-NEGOTIABLE)** | PASS | All download links are direct upstream CDN URLs. Server never buffers or relays media files. |
| **IV. Testability & Offline Verification** | PASS | Full test suite in `tests/test_assistant.py` using `respx` to mock LLM completions and web search responses. |
