# Quickstart: Favorites Page Validation Guide

**Feature**: `010-favorites-page` | **Date**: 2026-10-03 | **Spec**: [spec.md](./spec.md) | **Data Model**: [data-model.md](./data-model.md) | **Contracts**: [heart-toggles.md](./contracts/heart-toggles.md)

## Purpose

This guide provides runnable validation scenarios that prove the Favorites feature works end-to-end. It assumes implementation completed (components, page, hook produced by subsequent tasks) and verifies against all FR and SC acceptance criteria.

## Prerequisites

- Web app running locally (e.g., `npm run dev --workspace=apps/web`)
- Browser (Chrome recommended for DevTools inspection)
- Optional: existing `linkschin:watchlist` in localStorage for migration validation
- Debugger/Playwright for automated tests (optional)

## Scenarios

### Scenario 1: Like a movie from hero (P1 — core toggle)

**Steps:**

1. Open `http://localhost:3000` in desktop browser (or app port)
2. Confirm homepage displays hero banner ("Digger", "Uprising", etc.)
3. Click the heart-outline button labeled "Add to favorites"
4. Verify: Heart fills (rose-colored), button label changes to "Remove from favorites"
5. Reload the page (`Cmd+R` / `F5`)
6. Verify: Heart remains filled (persisted), button still says "Remove from favorites"

**Expected Outcome:**

- Toggle instant (<100ms)
- localStorage key `linkschin:favorites` contains movie ID
- Reload preserves state

**Relevant Spec**: US-1, FR-001, FR-002, FR-006

---

### Scenario 2: Unlike from same hero (P1 — reversible)

**Steps:**

1. From Scenario 1's state (movie liked), click the same heart (now filled)
2. Verify: Heart un-fills, button label returns to "Add to favorites"
3. Check DevTools → Application → Local Storage → `linkschin:favorites`
4. Verify: Movie ID no longer in `items` array (or array empty)

**Expected Outcome:**

- Unlike instant (<100ms)
- No leftover references in storage

**Relevant Spec**: US-1 Acceptance Scenario #2

---

### Scenario 3: Open favorites from header (P1 — navigation)

**Steps:**

1. Like at least one item (any category) from homepage
2. Click the "Favorites" header link (heart icon, replaces old "Watchlist")
3. Verify: Browser navigates to `/favorites` (new address, not anchor scroll or tab)
4. Use Back button (`Alt+←` or browser back)
5. Verify: Returns to previous page context

**Expected Outcome:**

- `/favorites` renders as full standalone page with header/footer
- No `#watchlist` anchor behavior
- Back navigation works

**Relevant Spec**: US-2, FR-003

---

### Scenario 4: Favorites grouped by category (P2 — grouping)

**Setup:** Like 1 movie + 1 game + 1 music item

**Steps:**

1. Open `/favorites`
2. Verify: Three separate headings — "Movies", "Games", "Music" — each with correct per-group count (e.g., "1 saved" or Persian localized equivalent)
3. Verify: Each liked item appears under its correct group only
4. Click an item card → detail drawer/modal opens with same item data
5. Unlike the item from the details view
6. Verify: Item disappears from favorites page immediately (no reload)

**Expected Outcome:**

- Grouping exact; counts accurate
- Cross-page (home vs favorites) state sync within 50ms

**Relevant Spec**: US-3, FR-004, FR-005

---

### Scenario 5: Single-category liked set (P2 — partial groups)

**Steps:**

1. Clear all likes (manually remove `linkschin:favorites` from localStorage, reload)
2. Like only 1 movie (no games/music)
3. Open `/favorites`
4. Verify: Movies group shows content; Games/Music groups show empty placeholders or are hidden (per implementation detail)

**Expected Outcome:**

- No confusion; user understands only movies are liked

**Relevant Spec**: US-3 Acceptance Scenario #2

---

### Scenario 6: Empty favorites state (P3 — first run)

**Steps:**

1. Clear `linkschin:favorites` from localStorage (and no watchlist present)
2. Open `/favorites` directly
3. Verify: Friendly empty-state card displays: "Nothing saved yet" + explanation of how to like items + link/button back to home/catalog

**Expected Outcome:**

- No blank page; guidance text visible
- No console errors

**Relevant Spec**: US-4, FR-009

---

### Scenario 7: Migration from watchlist (legacy users)

**Setup:** In localStorage, set `linkschin:watchlist` = `["digger","baldurs-gate-3","sogand"]`, delete any `linkschin:favorites`

**Steps:**

1. Reload homepage (`/`)
2. Verify: All three items now show filled hearts (liked state)
3. Open `/favorites`
4. Verify: All three items present, grouped correctly
5. Check localStorage: `linkschin:favorites.items` contains all three IDs; `linkschin:watchlist` key deleted

**Expected Outcome:**

- Zero data loss; all legacy entries carry over
- Migration happens once (metadata.migratedFromWatchlist = true)

**Relevant Spec**: Edge Case #4, FR-007, SC-003

---

### Scenario 8: Corrupt storage resilience

**Setup:** Set `linkschin:favorites` = `"not-valid-json{["` in localStorage

**Steps:**

1. Reload `/` or `/favorites`
2. Verify: Page loads normally, no errors in console
3. Click a heart to like an item
4. Verify: Like succeeds in-session; toast may note "starting fresh"

**Expected Outcome:**

- Graceful degradation, no broken page

**Relevant Spec**: Edge Case #2, FR-010

---

### Scenario 9: Unavailable/stale liked item

**Setup:** Manually add a fake ID (e.g., `"ghost-item-xyz"`) to `linkschin:favorites.items`

**Steps:**

1. Open `/favorites`
2. Verify: Page renders; ghost entry shows as "Unavailable" card with remove button (not crash)
3. Click remove
4. Verify: Entry disappears, storage updated

**Expected Outcome:**

- Resilient rendering per FR-010

**Relevant Spec**: Edge Case #1, FR-010

---

### Scenario 10: No watchlist remnants (regression check)

**Steps:**

1. Search entire UI for visible "Watchlist" text or bookmark-save icon
2. Verify: Zero occurrences — header shows "Favorites" + heart; hero says "Add to favorites"; home has no `#watchlist` section; footer no watchlist link

**Expected Outcome:**

- Complete terminology swap per FR-008

**Relevant Spec**: FR-008, SC-004

---

## Automated Test Pointers

- **Component tests** (Vitest): `useFavorites` hook — like/unlike, migration, corrupt handling
- **E2E** (Playwright): Scenarios 1–4, 6, 7, 10 as happy-path regression suite
- **Manual only**: Scenarios 8–9 (storage edge cases easier to inject manually)

## Quick Validation Commands

```bash
# Check localStorage in browser console
localStorage.getItem('linkschin:favorites')

# Verify migration
JSON.parse(localStorage.getItem('linkschin:watchlist') || '[]')

# Count liked groups
JSON.parse(localStorage.getItem('linkschin:favorites')).items.length

# Inspect per-category breakdown on /favorites
document.querySelectorAll('section[data-category]').length
```
