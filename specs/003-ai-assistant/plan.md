# Implementation Plan: AI Conversational Search Assistant

**Branch**: `003-ai-assistant` | **Date**: 2026-09-29 | **Spec**: [specs/003-ai-assistant/spec.md](spec.md)

**Input**: Feature specification from `/specs/003-ai-assistant/spec.md`

## Summary

Implement an intelligent AI conversational search assistant accessible via a lightweight, floating web widget. The assistant translates natural language prompts into multi-term candidate queries and queries the existing Python search engine as its primary tool. If local catalog results are empty, it autonomously falls back to a web search discovery tool, validates direct CDN download links, and ingests newly discovered items into the central SQLite FTS5 index for future immediate retrieval. All media links remain direct client-to-CDN (zero server media relaying).

## Technical Context

**Language/Version**: Python >= 3.11, Vanilla Modern JavaScript (ES6+), Vanilla CSS
**Primary Dependencies**: FastAPI (>=0.110.0), Uvicorn, Jinja2, HTTPX (>=0.27.0), Selectolax (>=0.3.21), SQLite3 (stdlib)
**Storage**: SQLite FTS5 (`apps/api/data/index.db`) with WAL mode
**Testing**: pytest (>=8.0.0), pytest-asyncio, respx (for offline HTTP/LLM mocking)
**Target Platform**: Linux / macOS server, modern web browsers (desktop and mobile)
**Project Type**: Web service with integrated conversational assistant and client widget
**Performance Goals**: <3.0s response for catalog hits (p90), <8.0s for web search fallback (p85), <150ms widget initialization
**Constraints**: Zero server-side media buffering/relaying (Constitution III), no npm/Node SPA build pipelines (Constitution II), offline testable with mocked fixtures (Constitution IV)
**Scale/Scope**: Single lightweight agent loop (<200 LOC), 1 new endpoint (`/api/chat`), 1 Jinja2 template partial, 1 vanilla JS script, 1 CSS stylesheet

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Requirement | Plan Alignment | Status |
|-----------|-------------|----------------|--------|
| **I. Library / Module Isolation** | Isolated plugins; no cross-dependency | Assistant logic isolated under `apps/api/assistant/` (`agent.py`, `tools.py`, `web_search.py`). Interacts with `db.py` and `sources/` via public API. | PASS |
| **II. Simplicity / YAGNI** | Server-rendered HTML (Jinja2), vanilla CSS, no Node/npm SPA build pipelines, in-memory caching | Assistant widget is a Jinja2 partial + vanilla JS (<250 lines) + CSS. Backend uses existing `httpx` and `selectolax`. Zero new packages. | PASS |
| **III. No Media Relaying (NON-NEGOTIABLE)** | Server acts solely as metadata aggregator; never buffer, proxy, or relay media | Assistant returns direct CDN URLs. Web discovery filters for direct links only. 0 bytes of media pass through server. | PASS |
| **IV. Testability & Offline Verification** | Verifiable offline with mocked HTTP clients (`respx`) | All LLM endpoints, search engine calls, and web search responses mocked via `respx` in `tests/test_assistant.py`. Tests run fully offline. | PASS |

## Project Structure

### Documentation (this feature)

```text
specs/003-ai-assistant/
├── plan.md              # This file (/speckit-plan output)
├── research.md          # Phase 0 output: architecture decisions
├── data-model.md        # Phase 1 output: schemas & tool definitions
├── quickstart.md        # Phase 1 output: verification guide
├── contracts/           # Phase 1 output: API OpenAPI specification
│   └── chat-api.yaml
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
apps/api/
├── assistant/                   # AI assistant subsystem
│   ├── __init__.py
│   ├── agent.py                 # Tool-calling agent loop (httpx-based)
│   ├── models.py                # Pydantic schemas & tool definitions
│   ├── tools.py                 # search_catalog & index_media adapters
│   └── web_search.py            # Fallback web discovery scraper
├── data/
│   └── index.db                 # SQLite FTS5 database (existing)
├── web/
│   ├── app.py                   # FastAPI app (mounts /api/chat)
│   ├── static/
│   │   ├── chat_widget.css      # Floating widget styles
│   │   └── chat_widget.js       # Vanilla ES6 streaming client
│   └── templates/
│       ├── _chat_widget.html    # Widget Jinja2 partial
│       └── base.html            # Includes _chat_widget.html
└── tests/
    └── test_assistant.py        # Offline mocked tests (respx)
```

**Structure Decision**:
All assistant logic is organized as an isolated sub-package (`apps/api/assistant/`) within the existing FastAPI backend. The UI widget lives in the existing `apps/api/web/` template and static assets directory, adhering to the monorepo conventions without introducing any frontend build frameworks.

## Complexity Tracking

> **Constitution check passed with 0 violations. No complexity exemptions required.**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None      | N/A        | N/A                                 |
