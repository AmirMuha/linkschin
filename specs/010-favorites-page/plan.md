# Implementation Plan: Favorites Page

**Branch**: `010-favorites-page` | **Date**: 2026-10-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-favorites-page/spec.md`

## Summary

Replace the watchlist section on the homepage with a dedicated standalone Favorites page at `/favorites`. Users mark items as liked using a heart icon (from lucide-react) instead of the bookmark icon, and clicking the header link opens their favorites page showing liked movies, games, and music grouped by category in separate sections. The feature reuses existing catalog lookup (`getCatalogItemById`), persists likes to localStorage (same mechanism as current watchlist), and migrates all existing watchlist entries to likes on first load. No backend changes required — entirely frontend implementation within the Next.js app.

## Technical Context

**Language/Version**: TypeScript 5.x / React 18+ (Next.js 14 App Router style conventions, client components via `'use client'`)

**Primary Dependencies**: 
- `lucide-react`: Heart icon replaces Bookmark for like actions (already installed v0.475.0+)
- Tailwind CSS: Existing utility-first styling throughout apps/web
- Next.js: Built-in routing (`/favorites` page added)
- LocalStorage: Same persistence mechanism as current watchlist

**Storage**: None required; client-side only persistence via localStorage

**Testing**: Vitest + Playwright (project standard); component tests for heart toggle behavior, E2E for favorites navigation flow

**Target Platform**: Modern browsers (Chrome/Firefox/Safari/Edge); same constraints as existing Next.js app

**Project Type**: Next.js web application within Turborepo monorepo

**Performance Goals**: <1s page load for favorites list; instant heart-toggle feedback (<100ms per action); graceful empty/corrupt-state handling without errors

**Constraints**: Client-side only (localStorage); no server API endpoints needed; must maintain accessibility standards (keyboard operable, ARIA labels)

**Scale/Scope**: Per-device storage capacity (localStorage quota ~5MB); typically supports 500+ liked items comfortably

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Relevant Constitution Principles:**

- **I. Library / Module Isolation**: N/A — feature is UI-only, no scraper plugins involved.
- **II. Simplicity / YAGNI & Monorepo Platform Structure**: PASS — feature uses existing Next.js infrastructure, no new dependencies, local storage only.
- **III. No Media Relaying (NON-NEGOTIABLE)**: PASS — feature has zero media transport responsibilities.
- **IV. Testability & Offline Verification**: PASS — localStorage fixtures support offline testing of like/unlike flows.

**GATE STATUS**: All gates passed. Proceeding with full implementation scope.

## Project Structure

### Documentation (this feature)

```text
specs/010-favorites-page/
├── plan.md              # This file (/speckit-plan command output)
├── spec.md              # Feature specification
├── data-model.md        # Data model definitions
├── quickstart.md        # Validation guide
├── contracts/           # UI interaction contracts
│   └── heart-toggles.md
└── tasks.md             # Task breakdown (/speckit-tasks)
```

### Source Code (repository root)

```text
apps/web/src/
├── app/
│   ├── favorites/
│   │   └── page.tsx          # Standalone favorites page
│   ├── sources/
│   └── youtube-to-mp3/
├── components/
│   ├── Header.tsx            # Update: heart icon, activePage='favorites'
│   ├── HeroBanner.tsx        # Update: BookMark → Heart icon
│   ├── DetailDrawer.tsx      # Update: like/unlike action present
│   ├── CatalogCard.tsx       # Update: like button inline
│   └── ui/
│       └── ToastNotification.tsx  # Optional: migration toast
├── lib/
│   ├── catalog.ts            # No changes; reuse getCatalogItemById
│   └── api.ts                # No changes; no new API calls
└── hooks/
    └── useFavorites.ts       # Custom hook: like/unlike, migrate, localStorage access
```

**Structure Decision**: Single-page addition (`apps/web/src/app/favorites/page.tsx`) reusing existing catalog and localStorage pattern. No backend changes. New hook centralizes like/unlike logic for reuse across components.

## Complexity Tracking

> **No constitutional violations requiring justification.** Feature complexity is minimal (UI additions only).
