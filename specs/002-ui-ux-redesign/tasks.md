---

description: "Task list for modern web interface and UI/UX redesign implementation"
---

# Tasks: Modern Web Interface and UI/UX Redesign

**Input**: Design documents from `specs/002-ui-ux-redesign/` (`plan.md`, `spec.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md`)

**Prerequisites**: Turborepo monorepo with `apps/api` (FastAPI), Python 3.12+, Node.js 20+, pnpm 11+

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [TaskID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
- Exact file paths included in all task descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and monorepo workspace configuration

- [x] T001 Initialize `apps/web` Next.js 15 (App Router, React 19, TypeScript) package structure in `apps/web/package.json`
- [x] T002 [P] Configure Tailwind CSS, PostCSS, and dark-theme color tokens in `apps/web/tailwind.config.ts` and `apps/web/src/app/globals.css`
- [x] T003 [P] Setup TypeScript configuration and path aliases (`@/*`) in `apps/web/tsconfig.json`
- [x] T004 [P] Define shared TypeScript interfaces mirroring domain models (`MediaItem`, `MovieDownloadVariant`, `GameRelease`, `GamePartLink`, `MusicTrack`, `MusicDownloadVariant`, `SearchApiResponse`, `SourceStatus`) in `apps/web/src/types/media.ts`
- [x] T005 [P] Update root Turborepo pipeline configuration for `build`, `dev`, `lint`, and `check` tasks in `turbo.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure and backend JSON endpoints that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Expose typed JSON search endpoint `GET /api/search?q={query}&category={category}&refresh={bool}` with FastAPI CORSMiddleware in `apps/api/web/app.py`
- [x] T007 [P] Implement resilient HTTP fetch client with AbortController and timeout support in `apps/web/src/lib/api.ts`
- [x] T008 [P] Implement Persian/Arabic Unicode normalization (NFKC, `ي` → `ی`, `ك` → `ک`) in `apps/web/src/lib/persian.ts`
- [x] T009 [P] Implement clipboard utility using `navigator.clipboard.writeText` with textarea fallback for non-secure contexts in `apps/web/src/lib/clipboard.ts`
- [x] T010 [P] Create Toast notification manager and context for clipboard actions in `apps/web/src/components/ui/ToastNotification.tsx`
- [x] T011 Create AppShell layout with root `dir="rtl"`, Vazirmatn Persian font loading, and dark canvas background (`bg-slate-950`) in `apps/web/src/app/layout.tsx`
- [x] T012 [P] Create non-blocking skeleton loader cards with pulse animation in `apps/web/src/components/ui/SkeletonGrid.tsx`
- [x] T013 [P] Create source status indicator bar displaying active scraper status and timeout warnings in `apps/web/src/components/SourceStatusBar.tsx`

**Checkpoint**: Foundation ready - backend JSON API operational and frontend shell ready for user story implementation.

---

## Phase 3: User Story 1 - Cinematic Media Discovery, Filtering & Direct Video Links (Priority: P1) 🎯 MVP

**Goal**: Deliver the primary movie and series discovery experience with instant search, quality/audio filtering, formatted download variant cards, and direct video streaming preview.

**Independent Test**: Search for a movie title (e.g. `Inception` or `تلقین`), view poster artwork, synopsis, and release year, filter variants by resolution (1080p, 720p), copy direct download link to clipboard with toast confirmation, and initiate an opportunistic stream preview in under 3 clicks without server proxying.

### Implementation for User Story 1

- [x] T014 [P] [US1] Create category navigation and search bar with clear button, submit trigger, and `/` or `Ctrl+K` focus shortcut in `apps/web/src/components/SearchBar.tsx`
- [x] T015 [P] [US1] Create in-view filter bar for resolution (`4K`, `1080p`, `720p`, `480p`), audio track (`دوبله فارسی`, `زیرنویس چسبیده`), and source filtering in `apps/web/src/components/InViewFilterBar.tsx`
- [x] T016 [P] [US1] Create movie download variant matrix component grouping links by resolution, codec, audio track, and size with copy-link and direct download triggers in `apps/web/src/components/cards/MovieDownloadMatrix.tsx`
- [x] T017 [P] [US1] Create accessible video stream preview modal with native HTML5 `<video>` for items with valid `stream_url` in `apps/web/src/components/player/VideoPlayerModal.tsx`
- [x] T018 [US1] Create MovieCard component integrating poster artwork, localized Persian/English titles, year badge, synopsis, stream preview trigger, and download matrix in `apps/web/src/components/cards/MovieCard.tsx`
- [x] T019 [US1] Implement main search results grid and state wiring for Movies in `apps/web/src/app/page.tsx`
- [ ] T020 [US1] Validate Scenario 1 (Movie Discovery & Quality Filter) and Scenario 5 (Direct CDN Invariant) from `specs/002-ui-ux-redesign/quickstart.md`

**Checkpoint**: User Story 1 is fully functional and testable independently as the standalone MVP.

---

## Phase 4: User Story 2 - Multi-Part Game Archive Management & Batch Link Exporter (Priority: P1)

**Goal**: Deliver a specialized game repack and archive viewer displaying sequential archive parts with individual sizes, extraction password with 1-click copy, missing part detection, and newline-separated batch link export for download managers.

**Independent Test**: Search for a game title (e.g. `Cyberpunk` or `GTA`), open game release card, verify parts are listed in strictly increasing numerical order (`Part 1`, `Part 2`, ...), copy password to clipboard via dedicated button, and export all direct URLs via "Copy All Links" to paste into external download managers.

### Implementation for User Story 2

- [x] T021 [P] [US2] Implement sequential archive part validation ensuring `part_number` continuity and populating `has_missing_parts` and `missing_part_numbers` in `apps/web/src/lib/archive.ts`
- [x] T022 [P] [US2] Create high-visibility archive password pill with 1-click copy button and toast confirmation in `apps/web/src/components/cards/PasswordPill.tsx`
- [x] T023 [P] [US2] Create GamePartList component displaying sequential parts, individual sizes, single part copy buttons, missing parts warning alert, and "Copy All Links" action in `apps/web/src/components/cards/GamePartList.tsx`
- [x] T024 [US2] Create GameCard component integrating cover art, release group, version, total size, password pill, and part list in `apps/web/src/components/cards/GameCard.tsx`
- [x] T025 [US2] Wire Games category tab and result card rendering into `apps/web/src/app/page.tsx`
- [ ] T026 [US2] Validate Scenario 2 (Game Multi-Part Archive & Batch Link Copy) from `specs/002-ui-ux-redesign/quickstart.md`

**Checkpoint**: User Stories 1 AND 2 are both fully functional and testable independently.

---

## Phase 5: User Story 3 - Inline Audio Audition & Direct Music Download (Priority: P2)

**Goal**: Deliver an instant audio auditioning experience with an inline track player, persistent sticky bottom player bar, single-instance playback guarantee, and bitrate-selective download buttons.

**Independent Test**: Search for a song or artist, click inline play icon, verify audio plays immediately with time scrubber and volume control, verify playing a second track halts the first, and verify 128kbps and 320kbps download buttons link directly to CDN.

### Implementation for User Story 3

- [x] T027 [P] [US3] Implement global AudioPlayerContext managing a single HTML5 `Audio` instance, playback state, scrubber time, duration, and volume persisted in `localStorage` in `apps/web/src/context/AudioPlayerContext.tsx`
- [x] T028 [P] [US3] Create sticky GlobalAudioPlayer bar with play/pause, time scrubber, volume slider, track title, artist, and close trigger in `apps/web/src/components/player/GlobalAudioPlayer.tsx`
- [x] T029 [P] [US3] Create MusicDownloadRow component displaying distinct 320kbps and 128kbps download badges with file sizes in `apps/web/src/components/cards/MusicDownloadRow.tsx`
- [x] T030 [US3] Create MusicCard component integrating cover art, artist, title, inline play/pause trigger, and bitrate download options in `apps/web/src/components/cards/MusicCard.tsx`
- [x] T031 [US3] Wire Music category tab and GlobalAudioPlayer mounting into `apps/web/src/app/page.tsx`
- [ ] T032 [US3] Validate Scenario 3 (Audio Track Audition & Single-Instance Playback) from `specs/002-ui-ux-redesign/quickstart.md`

**Checkpoint**: User Stories 1, 2, and 3 are all operational and testable.

---

## Phase 6: User Story 4 - Accessible, Responsive Bilingual (RTL/LTR) Shell & Keyboard Navigation (Priority: P2)

**Goal**: Ensure the web platform delivers a polished, accessible, bilingual experience across mobile and desktop, strictly isolating LTR technical text to prevent punctuation inversion, and supporting keyboard shortcuts.

**Independent Test**: Test viewports from 375px to 1440px, verifying Persian text flows RTL, technical filenames and codecs remain isolated LTR without inverted punctuation, `/` or `Ctrl+K` focuses the search bar, `Escape` clears or dismisses modals, and all interactive elements meet 44x44px touch targets.

### Implementation for User Story 4

- [x] T033 [P] [US4] Create TechnicalText component enforcing strict `dir="ltr"` and `unicode-bidi: isolate` with monospace styling for filenames, release hashes, codecs, and URLs in `apps/web/src/components/ui/TechnicalText.tsx`
- [x] T034 [P] [US4] Implement global keyboard shortcuts hook (`/` and `Ctrl+K` / `Cmd+K` for search focus, `Escape` for blur/close) in `apps/web/src/hooks/useKeyboardShortcuts.ts`
- [x] T035 [US4] Audit CSS touch targets (minimum 44x44px on mobile) and high-contrast visible focus rings across inputs, buttons, and badges in `apps/web/src/app/globals.css`
- [ ] T036 [US4] Validate Scenario 4 (Responsive Bidirectional Layout & Keyboard Shortcuts) from `specs/002-ui-ux-redesign/quickstart.md`

**Checkpoint**: All user stories complete with full accessibility and bidirectional layout compliance.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Enhancements that span multiple user stories, caching controls, and final verification

- [x] T037 [P] Implement "تازه‌سازی" (Force Refresh) button in search bar passing `refresh=true` to bypass cache in `apps/web/src/components/SearchBar.tsx`
- [x] T038 [P] Implement recent search history stored in `localStorage` with quick-select chips in `apps/web/src/lib/history.ts`
- [x] T039 Run backend pytest suite with offline fixtures ensuring zero regression in `apps/api/tests/`
- [ ] T040 Run frontend TypeScript check (`pnpm --filter @repo/web check` or `tsc --noEmit`) and Turborepo build (`pnpm build`)
- [ ] T041 Perform complete end-to-end walkthrough using `specs/002-ui-ux-redesign/quickstart.md` across all 5 verification scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - starts immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 completion - **BLOCKS all user stories**.
- **User Stories (Phase 3+)**:
  - **US1 (Phase 3)**: Depends on Phase 2. Can be deployed independently as the MVP.
  - **US2 (Phase 4)**: Depends on Phase 2 and SearchBar from US1. Can be developed in parallel with US3.
  - **US3 (Phase 5)**: Depends on Phase 2 and SearchBar from US1. Can be developed in parallel with US2.
  - **US4 (Phase 6)**: Polishes shell and cross-story layout across US1, US2, and US3 components.
- **Polish (Phase 7)**: Depends on all user stories being complete.

### Parallel Opportunities

- **Phase 1**: T002, T003, T004, T005 can execute concurrently once T001 creates directory structure.
- **Phase 2**: T007, T008, T009, T010, T012, T013 can execute in parallel while T006 adds the backend JSON route.
- **Phase 3 (US1)**: T014, T015, T016, T017 can be implemented in parallel before integrating into T018 and T019.
- **Phase 4 (US2)**: T021, T022, T023 can be implemented in parallel before assembling T024.
- **Phase 5 (US3)**: T027, T028, T029 can be implemented in parallel before assembling T030.
- **Phase 6 (US4)**: T033, T034 can be implemented in parallel before testing T035.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete **Phase 1: Setup** (initialize `apps/web`).
2. Complete **Phase 2: Foundational** (backend JSON endpoint in `apps/api/web/app.py`, API client, layout, and toast system).
3. Complete **Phase 3: User Story 1** (Movie search, format matrix, video preview).
4. **STOP and VALIDATE**: Execute Scenario 1 and Scenario 5 from `specs/002-ui-ux-redesign/quickstart.md`. Deploy/demo the working movie aggregator web interface.

### Incremental Delivery

1. Foundation + US1 → Working Movie Aggregator MVP.
2. Add US2 → Gamer workflow with multi-part archive display, password copy, and IDM batch exporter.
3. Add US3 → Music discovery with inline audio audition and bitrate-specific downloads.
4. Add US4 → Accessibility hardening, mobile touch target tuning, and keyboard navigation.
5. Polish → Force-refresh cache bypass, recent search history, and final test suite run.
