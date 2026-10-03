# Feature Specification: Favorites Page

**Feature Branch**: `010-favorites-page`

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "replace watchlist with favorite (likes , with heart icon) which when clicked shows a list of liked videos, games or musics in separate categories, it should be a new page not another tab content"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Like and unlike an item (Priority: P1)

A visitor browsing movies, games, or music marks an item they like using a heart control, and can remove the like the same way. The liked state is visible wherever the item appears.

**Why this priority**: This is the core interaction; without it there is nothing to show on the favorites page.

**Independent Test**: Can be fully tested by liking an item from a card/hero/detail view, confirming the heart shows the liked state, unliking it, and confirming the state clears — delivering a working like toggle with no favorites page needed.

**Acceptance Scenarios**:

1. **Given** an unliked movie, game, or music item, **When** the user activates its heart control, **Then** the item becomes liked and the heart shows the liked state.
2. **Given** a liked item, **When** the user activates its heart control again, **Then** the item becomes unliked and the heart returns to the unliked state.
3. **Given** a liked item shown in more than one place (e.g., hero banner and listing), **When** the user unlikes it in one place, **Then** all visible instances reflect the unliked state.

---

### User Story 2 - Open favorites from the header (Priority: P1)

A visitor clicks the Favorites entry (heart icon) in the site header and lands on a dedicated favorites page showing everything they liked.

**Why this priority**: This is the requested replacement for the watchlist entry point; it defines the new navigation.

**Independent Test**: Can be fully tested by liking at least one item, clicking the header Favorites entry, and confirming a standalone page opens at its own address — delivering the new destination even before category grouping is polished.

**Acceptance Scenarios**:

1. **Given** the site header on any page, **When** the user activates the Favorites entry, **Then** a dedicated favorites page opens (not a tab, section, or drawer inside another page).
2. **Given** the user is on the favorites page, **When** they use the browser back control, **Then** they return to the page they came from.

---

### User Story 3 - Browse liked items grouped by category (Priority: P2)

A visitor on the favorites page sees their liked videos/movies, games, and music grouped into separate categories, and can open any item's details from there.

**Why this priority**: Grouping is the requested organization of the list; it makes a mixed liked set usable.

**Independent Test**: Can be fully tested by liking one movie, one game, and one music item, opening the favorites page, and confirming three separate groups each containing the right item — delivering organized browsing.

**Acceptance Scenarios**:

1. **Given** liked items spanning movies, games, and music, **When** the user opens the favorites page, **Then** items appear under separate Movies, Games, and Music groups.
2. **Given** liked items in only one category, **When** the user opens the favorites page, **Then** only that category group shows content and empty groups are clearly marked or hidden without confusion.
3. **Given** a liked item on the favorites page, **When** the user activates it, **Then** its details view opens.

---

### User Story 4 - Empty favorites state (Priority: P3)

A visitor with no likes yet opens the favorites page and understands what it is for and how to add items.

**Why this priority**: First-run experience; prevents a blank page from looking broken.

**Independent Test**: Can be fully tested by opening the favorites page with no liked items and confirming guidance text plus a path back to browsing — delivering a complete empty state.

**Acceptance Scenarios**:

1. **Given** zero liked items, **When** the user opens the favorites page, **Then** an empty-state message explains that nothing is liked yet and how to like items.

---

### Edge Cases

- What happens when a previously liked item no longer exists in the catalog (removed/renamed)? It must not break the page; the entry is shown as unavailable or skipped, and the user can remove it.
- How does the page handle a corrupt or unreadable saved likes store? The page loads with an empty list rather than failing, and liking still works for the session.
- What happens when storage is unavailable (private mode, quota exceeded)? The like toggle still works in-session, and the limitation is communicated rather than silently failing.
- What happens to existing watchlist entries from before this feature? They carry over as liked items so no saved entry is lost.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST let users mark any movie, game, or music item as liked and remove the like, using a heart control in every place items are actionable (cards, hero banner, detail view).
- **FR-002**: System MUST display the liked state on the heart control (filled/active vs. outline/inactive) consistently wherever the item appears.
- **FR-003**: System MUST provide a header navigation entry labeled Favorites with a heart icon that opens a dedicated standalone favorites page (its own address), replacing the previous watchlist link and its in-page anchor section.
- **FR-004**: Favorites page MUST group liked items into separate Movies (videos), Games, and Music categories, each with its own heading and count.
- **FR-005**: Favorites page MUST let users open an item's details from any grouped entry and remove the like from either the grouped entry or the details view, with the page updating immediately.
- **FR-006**: System MUST persist liked items across sessions on the same device and browser.
- **FR-007**: System MUST migrate existing saved watchlist entries into liked items on first load after the change, preserving every previously saved entry.
- **FR-008**: System MUST remove all watchlist terminology and bookmark-icon affordances for saving items (labels, header link, in-page section, empty-state copy), replacing them with Favorites/likes and the heart icon.
- **FR-009**: Favorites page MUST present a clear empty state when no items are liked, explaining how to add likes and offering a way back to browsing.
- **FR-010**: Favorites page MUST remain fully usable when liked entries reference items missing from the catalog (show as unavailable with a removal option, never a broken page).

### Key Entities

- **Liked Item**: A user-saved reference to a catalog entry; attributes: item identity, category (movie/video, game, music), date liked. One user collection per device; no sharing or accounts.
- **Favorites Page**: A standalone page presenting the liked-item collection grouped by category, with per-group counts, iwtem details entry points, and unlike actions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can like an item and find it grouped under the correct category on the favorites page in under 30 seconds on a first attempt.
- **SC-002**: 90% of first-time users who like items across all three categories can locate each item under its correct group without assistance.
- **SC-003**: Zero previously saved watchlist entries are lost during migration (all carry over as liked items).
- **SC-004**: No watchlist label, bookmark save icon, or in-page watchlist section remains reachable in the interface.

## Assumptions

- Likes are per-device/per-browser with no accounts, sync, or server-side storage; the same durability users get from the current watchlist.
- The three categories are Movies (videos), Games, and Music, matching the existing catalog categories.
- The heart icon follows the existing icon set and visual language; exact artwork is a design detail.
- The favorites page is a standalone page with its own address and reuses the existing header/footer chrome; the exact address is an implementation detail.
- Migration is one-way: once watchlist entries become likes, the old watchlist store is retired.
- Catalog item identity and category lookup reuse the existing catalog; no new content model.
- Accessibility basics apply: heart controls and grouped lists are keyboard-operable with discernible labels.
