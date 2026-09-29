# Implementation Plan: User Source Suggestion Form

**Branch**: `004-source-suggestions` | **Date**: 2026-09-29 | **Spec**: [specs/004-source-suggestions/spec.md](spec.md)

**Input**: Feature specification from `specs/004-source-suggestions/spec.md`

## Summary

Implement a lightweight, submittable media source suggestion form in `apps/web` connected to `apps/api`. Submissions are validated and stored in `apps/api/data/index.db` using stdlib `sqlite3`. Features include canonical domain deduplication with request counter upvoting, rolling 24-hour IP rate limiting (10 submissions/day), and an authenticated maintainer API endpoint (`GET /api/admin/suggestions`) secured with an `X-Admin-Token` header.

## Technical Context

**Language/Version**: Python 3.12 (Backend `apps/api`), TypeScript 5.6+ / Node.js 20+ (Frontend `apps/web`)

**Primary Dependencies**: FastAPI, Pydantic, Uvicorn, stdlib `sqlite3`, Next.js 15, React 19, Tailwind CSS, Lucide React

**Storage**: SQLite (`apps/api/data/index.db`) via stdlib `sqlite3` (no external DB servers or ORMs)

**Testing**: `pytest` (backend API & DB logic), `pnpm test` (frontend components & validation)

**Target Platform**: Linux / Container / Modern Web Browsers

**Project Type**: Monorepo Web Application (FastAPI backend + Next.js frontend)

**Performance Goals**: < 50ms API submission latency; zero impact on search index performance

**Constraints**: Zero new external runtime dependencies; strict compliance with Project Constitution Principle II (Simplicity / YAGNI) and Principle III (No Media Relaying)

**Scale/Scope**: < 100 submissions/month; ~1 modal UI component, 2 API endpoints, 1 database table

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Principle I: Library / Module Isolation**: N/A (Not a scraper under `sources/`; standard web endpoint and UI modal).
- [x] **Principle II: Simplicity / YAGNI & Monorepo Platform Structure**: PASS. Zero new dependencies; uses stdlib `sqlite3` and existing Next.js + Tailwind components. No message queues, Redis, or external DBs.
- [x] **Principle III: No Media Relaying**: PASS. Only collects website metadata (URL, category, notes); handles zero audio/video streaming or downloading.
- [x] **Principle IV: Testability & Offline Verification**: PASS. Backend tests run against in-memory SQLite (`:memory:`) without network dependencies.

## Project Structure

### Documentation (this feature)

```text
specs/004-source-suggestions/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output: Technical decisions & rationale
├── data-model.md        # Phase 1 output: Schema & entity model
├── quickstart.md        # Phase 1 output: Runnable validation scenarios
└── contracts/           # Phase 1 output: REST API contracts
    └── suggestions-api.json
```

### Source Code (repository root)

```text
apps/api/
├── db.py                               # SQLite schema & DB helpers for source_suggestions
├── models.py                           # Pydantic schemas (SourceSuggestionCreate, SourceSuggestionOut)
├── web/
│   └── app.py                          # POST /api/sources/suggest, GET /api/admin/suggestions
└── tests/
    └── test_suggestions.py             # Unit & integration tests for submission, rate limiting, and admin

apps/web/
├── src/
│   ├── lib/
│   │   └── api.ts                      # suggestSource() client API call
│   ├── components/
│   │   ├── SourceStatusBar.tsx         # "Suggest a Source" trigger button
│   │   └── SourceSuggestModal.tsx      # Modal form component with validation & toast feedback
│   └── types/
│       └── media.ts                    # TypeScript types for suggestion submission
```

**Structure Decision**: Monorepo web application using existing `apps/api` and `apps/web` packages. All new endpoints and components live directly inside existing directory structures without introducing new services or subprojects.

## Complexity Tracking

*No violations. All design choices strictly adhere to the Constitution and minimal-dependency rules.*
