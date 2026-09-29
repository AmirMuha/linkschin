# Implementation Plan: Modern Web Interface and UI/UX Redesign

**Branch**: `002-ui-ux-redesign` | **Date**: 2026-09-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-ui-ux-redesign/spec.md`

## Summary

Build a modern, high-contrast web interface (`apps/web`) using Next.js (App Router), React, TypeScript, and Tailwind CSS within the existing Turborepo monorepo, paired with JSON API endpoints exposed by the existing FastAPI aggregator backend (`apps/api`). The interface delivers a cinematic media discovery experience across Movies, Games, and Music with bidirectional RTL/LTR Persian typography (Vazirmatn), an inline audio preview player, one-click download manager link export for split game archives, format-grouped download badges, and strict compliance with the zero-relay direct CDN constraint (Constitution Principle III).

---

## Technical Context

**Language/Version**:
- Backend: Python `3.12+`
- Frontend: TypeScript `5.0+`, Node.js `20+` (running on Node `v26.7.0` / pnpm `v11.3.0`)

**Primary Dependencies**:
- Backend: `fastapi`, `uvicorn`, `httpx`, `selectolax`, `cachetools`
- Frontend: `next` (App Router), `react`, `react-dom`, `tailwindcss`, `lucide-react`, `@radix-ui/react-dialog`, `@radix-ui/react-tabs`

**Storage**:
- Backend: SQLite (`movie_fetcher.db` with FTS5 search) + in-memory `TTLCache`
- Frontend: Browser `localStorage` (audio player volume, recent search history)

**Testing**:
- Backend: `pytest` with `respx` and offline HTML fixtures
- Frontend: `vitest` / React Testing Library, ESLint, TypeScript compiler (`tsc --noEmit`)

**Target Platform**:
- Server: Linux / POSIX server container
- Client: Modern evergreen web browsers (Chrome, Firefox, Safari, Edge) on desktop and mobile viewports (375px to 1440px+)

**Project Type**: Full-stack web application in a Turborepo monorepo (`apps/api` + `apps/web`)

**Performance Goals**:
- Cached search first meaningful paint < 1.5 seconds
- Fresh multi-source search skeleton feedback < 500ms, completing within the 10-second global scraper budget
- Smooth 60fps UI transitions, hover states, and audio progress scrubbing

**Constraints**:
- **Constitution Principle III (Non-Negotiable)**: 0% of audio, video, or archive bytes relayed or proxied through the aggregator server; strictly direct client-to-CDN connections
- **Accessibility**: WCAG 2.1 AA compliance, minimum 4.5:1 text contrast on dark canvas, minimum 44x44px touch targets on mobile
- **Bidirectional Typography**: Flawless Persian RTL reading flow with strictly isolated LTR technical filenames, codecs, hashes, and URLs (0 punctuation inversion defects)

**Scale/Scope**:
- Multi-category portal (Movies, Games, Music) supporting 4+ active scraper sources (`UpTVs`, `Doostihaa`, `YasDL`, `Nex1Music`) with concurrent extraction and error resilience

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evaluation & Mitigations |
|-----------|--------|--------------------------|
| **I. Library / Module Isolation** | **PASS** | Scraper sources remain completely isolated plugins under `apps/api/sources/` conforming to `SourcePlugin`. Frontend consumes them uniformly via the aggregated JSON API. |
| **II. Simplicity / YAGNI** | **AMENDED & PASS** | *Constitution Amendment*: The original Jinja2 template approach is superseded by a Next.js web application in `apps/web` to fulfill user requirements for interactive audio audition, instant format filtering, and clipboard batch export. Minimal dependencies are enforced (native HTML5 audio/video over heavy libraries, utility-first Tailwind CSS, no redundant BFF or external state managers). |
| **III. No Media Relaying (NON-NEGOTIABLE)** | **PASS** | All media streaming and file downloads link directly to upstream CDNs. The backend only extracts metadata and links; `apps/web` renders native `<a href download>` and direct HTML5 audio/video elements. |
| **IV. Testability & Offline Verification** | **PASS** | Backend scrapers continue to be verified offline using static HTML fixtures (`respx`). Frontend components can be verified with mock JSON responses without live internet dependencies. |

---

## Project Structure

### Documentation (this feature)

```text
specs/002-ui-ux-redesign/
├── checklists/
│   └── requirements.md  # Specification quality checklist
├── contracts/
│   ├── api-contract.md  # Backend REST API endpoints & JSON payloads
│   └── ui-contracts.md  # Component hierarchy, props, and interaction contracts
├── data-model.md        # Shared domain models & client UI state
├── plan.md              # This implementation plan
├── quickstart.md        # Runnable validation and end-to-end test guide
├── research.md          # Technical research and architectural decisions
└── spec.md              # Feature specification
```

### Source Code (repository root)

```text
movie-fetcher/
├── apps/
│   ├── api/                     # Python / FastAPI aggregator service
│   │   ├── sources/             # Standalone scraper plugins (UpTVs, YasDL, etc.)
│   │   ├── web/
│   │   │   └── app.py           # FastAPI app (exposes /api/search, /api/sources, /api/health)
│   │   ├── cache.py             # In-memory TTL cache & Persian normalization
│   │   ├── db.py                # SQLite persistent storage & FTS5 search
│   │   ├── http_client.py       # Robust async HTTP client with retry/proxy
│   │   ├── models.py            # Domain models (MediaItem, GameRelease, etc.)
│   │   └── tests/               # Offline pytest suite with static fixtures
│   │
│   └── web/                     # Next.js 15 modern web interface
│       ├── public/              # Static assets, icons, brand artwork
│       ├── src/
│       │   ├── app/             # App Router (layout.tsx, page.tsx, globals.css)
│       │   ├── components/      # UI components
│       │   │   ├── AppShell.tsx
│       │   │   ├── SearchBar.tsx
│       │   │   ├── CategoryNav.tsx
│       │   │   ├── InViewFilterBar.tsx
│       │   │   ├── SourceStatusBar.tsx
│       │   │   ├── cards/
│       │   │   │   ├── MovieCard.tsx
│       │   │   │   ├── GameCard.tsx
│       │   │   │   └── MusicCard.tsx
│       │   │   ├── player/
│       │   │   │   ├── GlobalAudioPlayer.tsx
│       │   │   │   └── VideoPlayerModal.tsx
│       │   │   └── ui/          # Badges, pills, toasts, skeletons
│       │   ├── hooks/           # useSearch, useAudioPlayer, useClipboard
│       │   ├── lib/             # API client, Persian text utilities, clipboard
│       │   └── types/           # Shared TypeScript interfaces mirroring models.py
│       ├── package.json
│       ├── tailwind.config.ts
│       └── tsconfig.json
│
├── package.json                 # Turborepo root package.json (pnpm)
├── pnpm-workspace.yaml          # Workspace definition (apps/*)
└── turbo.json                   # Turborepo task pipeline configuration
```

**Structure Decision**: The workspace uses Turborepo with two decoupled packages: `apps/api` (FastAPI backend service) and `apps/web` (Next.js frontend application). This preserves clear language boundaries while allowing unified monorepo orchestration (`pnpm dev`, `pnpm build`, `pnpm test`).

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Constitution Principle II Amendment (Next.js SPA vs Jinja2 HTML) | User specifically required a Next.js web platform with interactive audio player, clipboard manager exporter, format filters, and modern UI/UX. | Jinja2 full-page reloads cannot maintain persistent audio playback across searches, cannot provide interactive client-side quality filtering, and create clunky clipboard experiences. |
| Monorepo Workspace (`apps/web` + `apps/api`) | Clean architectural separation between Python scraping service and React frontend. | A monolithic Python-only or single-page script embeds frontend logic in backend templates, making modern UI maintenance and testing difficult. |
