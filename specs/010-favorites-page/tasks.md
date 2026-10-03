# Tasks: Favorites Page

**Input**: Design documents from `/specs/010-favorites-page/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Not requested in spec. Manual quickstart validation only.

**Organization**: Tasks grouped by user story. Each story independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1–US4)
- Exact file paths in every description

## Phase 1: Setup

**Purpose**: Branch and baseline verification

- [X] T001 Verify clean tree on current branch via `git status --short --branch` in /run/media/amirmuha/0C944DAF23695833/projects/linkschin
- [X] T002 Confirm `Heart` icon exists in installed lucide-react in apps/web/package.json

---

## Phase 2: Foundational — useFavorites hook + migration (BLOCKS all stories)

**Purpose**: Single shared likes store every component consumes. No story works without this.

**⚠️ CRITICAL**: No user story work until this phase complete.

- [X] T003 Create `useFavorites` hook in apps/web/src/hooks/useFavorites.ts with like/unlike/isLiked ids state, localStorage read/write under key `linkschin:favorites` shape `{ items: string[], metadata: {...} }` per data-model.md, corrupt-JSON→empty fallback, quota-failure→in-memory-only fallback
- [X] T004 Implement one-way watchlist migration in apps/web/src/hooks/useFavorites.ts: on first load copy `linkschin:watchlist` string[] into favorites items, set `metadata.migratedFromWatchlist=true`, delete old key, corrupt watchlist→start empty
- [X] T005 Wire `useFavorites` into apps/web/src/app/page.tsx replacing `watchlistIds`/`handleToggleWatchlist`/`isItemInWatchlist` state, keeping same component prop flow to HeroBanner and StaticSections

**Checkpoint**: Like/unlike an item on home, reload, state persists. Foundation ready.

---

## Phase 3: User Story 1 — Like and unlike an item (Priority: P1) 🎯 MVP

**Goal**: Heart toggle on every actionable item surface, consistent liked state everywhere.

**Independent Test**: Like item from card/hero/detail, confirm filled heart; unlike, confirm cleared; reload, confirm persistence (quickstart.md Scenarios 1–2).

- [X] T006 [P] [US1] Swap Bookmark→Heart toggle in apps/web/src/components/HeroBanner.tsx: outline heart + "Add to favorites" unliked, filled rose heart + "Remove from favorites" liked, aria-labels per contracts/heart-toggles.md
- [X] T007 [P] [US1] Add heart toggle button to apps/web/src/components/CatalogCard.tsx: corner overlay, `aria-pressed={isLiked}`, no navigation on click
- [X] T008 [US1] Add like/unlike action with toast + Undo to apps/web/src/components/DetailDrawer.tsx footer row per contracts/heart-toggles.md (depends on T003)
- [X] T009 [US1] Sync liked state across all visible instances in apps/web/src/app/page.tsx via shared hook (no per-component local copies)

**Checkpoint**: US1 fully functional standalone. MVP shippable.

---

## Phase 4: User Story 2 — Open favorites from header (Priority: P1)

**Goal**: Header heart entry opens standalone `/favorites` page; old watchlist anchor gone.

**Independent Test**: Like item, click header Favorites, land on own-address page; Back returns (quickstart.md Scenario 3).

- [X] T010 [US2] Replace watchlist anchor with Favorites link in apps/web/src/components/Header.tsx: `Heart` icon + "Favorites" label, `href="/favorites"`, `activePage` gains `'favorites'` value replacing `'watchlist'`
- [X] T011 [US2] Create standalone page shell in apps/web/src/app/favorites/page.tsx rendering Header (activePage favorites) + Footer + empty/grouped content slot
- [X] T012 [US2] Update footer watchlist link in apps/web/src/components/Footer.tsx: `#watchlist` → `/favorites`, label "Favorites"

**Checkpoint**: US1 + US2 work; header reaches empty favorites page.

---

## Phase 5: User Story 3 — Browse liked items grouped by category (Priority: P2)

**Goal**: `/favorites` groups Movies/Games/Music with counts, detail entry, instant unlike.

**Independent Test**: Like one of each category, confirm three correct groups; open details from group; unlike updates instantly (quickstart.md Scenarios 4–5).

- [X] T013 [US3] Render Movies/Games/Music groups with per-group counts in apps/web/src/app/favorites/page.tsx via `getCatalogItemById` lookup from apps/web/src/lib/catalog.ts
- [X] T014 [US3] Wire item→DetailDrawer opening and unlike-from-group/page refresh in apps/web/src/app/favorites/page.tsx (depends on T011)
- [X] T015 [US3] Render stale-id entries as unavailable-with-remove in apps/web/src/app/favorites/page.tsx per FR-010 (depends on T013)

**Checkpoint**: US1+US2+US3 work independently.

---

## Phase 6: User Story 4 — Empty favorites state (Priority: P3)

**Goal**: Zero-likes page explains itself with path back to browsing.

**Independent Test**: Clear storage, open `/favorites`, confirm guidance + home link, no errors (quickstart.md Scenario 6).

- [X] T016 [US4] Render empty-state card with guidance + browse link in apps/web/src/app/favorites/page.tsx when items list empty

**Checkpoint**: All stories independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Remove watchlist remnants, validate end to end.

- [X] T017 Remove watchlist section + `watchlistIds` prop from apps/web/src/components/StaticSections.tsx, keep remaining sections intact
- [X] T018 Remove watchlist copy ("Add to watchlist"/"In watchlist"/"Nothing saved yet" session text) in apps/web/src/components/HeroBanner.tsx and apps/web/src/components/StaticSections.tsx, replace with favorites wording per FR-008
- [X] T019 [P] Keyboard/ARIA pass on heart controls in apps/web/src/components/HeroBanner.tsx, apps/web/src/components/CatalogCard.tsx, apps/web/src/components/DetailDrawer.tsx, apps/web/src/app/favorites/page.tsx (focus ring, labels, `aria-pressed`)
- [X] T020 Run quickstart.md Scenarios 1–10 validation, fix failures before close

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all stories
- **User Stories (Phases 3–6)**: Depend on Foundational; run sequentially P1→P2→P3 or in parallel if staffed (US3/US4 need US2 shell T011)
- **Polish (Phase 7)**: Depends on all stories complete

### Within Each Story

- Hook/context before components (T003 before T006–T009)
- Page shell before grouped content (T011 before T013–T016)

### Parallel Opportunities

- T001, T002 in parallel
- T006, T007 in parallel (different files)
- T019 + quickstart prep alongside T017–T018 (different files)

---

## Parallel Example: User Story 1

```bash
Task: "Swap Bookmark→Heart toggle in apps/web/src/components/HeroBanner.tsx" (T006)
Task: "Add heart toggle button to apps/web/src/components/CatalogCard.tsx" (T007)
```

---

## Implementation Strategy

### MVP First (US1 + US2 shell)

1. Phase 1 Setup → Phase 2 Foundational (hook + migration + wiring)
2. Phase 3 US1 (heart toggles everywhere)
3. Phase 4 US2 (header link + `/favorites` shell)
4. **STOP and VALIDATE**: quickstart Scenarios 1–3
5. Deploy/demo

### Incremental Delivery

1. Setup + Foundational → persistence + migration live
2. + US1 → like/unlike works (MVP core)
3. + US2 → favorites destination reachable
4. + US3 → grouped browsing
5. + US4 → empty state
6. + Polish → zero watchlist remnants, Scenarios 1–10 green

---

## Notes

- Exact paths: `apps/web/src/hooks/useFavorites.ts` (new), `apps/web/src/app/favorites/page.tsx` (new), edits in `Header.tsx`, `HeroBanner.tsx`, `CatalogCard.tsx`, `DetailDrawer.tsx`, `StaticSections.tsx`, `Footer.tsx`, `app/page.tsx`
- No backend changes; no new dependencies (`Heart` already in lucide-react)
- Reuse `getCatalogItemById` from `apps/web/src/lib/catalog.ts` — do not reimplement
- Storage key `linkschin:favorites`; one-way migration from `linkschin:watchlist` then delete old key
- Commit after each task
