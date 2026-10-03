# Data Model: Favorites

**Feature**: `010-favorites-page` | **Date**: 2026-10-03 | **Spec**: [spec.md](./spec.md)

## Overview

This document defines the data structures for the Favorites feature: how liked items are stored locally, how they're retrieved from the catalog, and what constraints apply to each entity.

## Core Entities

### LikedItem

Represents a single user's saved/liked item in their personal favorites collection.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | Yes | Unique identifier; matches one of `CatalogMovie.id`, `CatalogGame.id`, or `CatalogMusic.id` |
| `category` | `'movies' \| 'games' \| 'music'` | Yes | Derived from catalog lookup at save time |
| `dateLiked` | number | No | Unix timestamp in milliseconds; auto-generated when first saved |

**Validation Rules:**

- `id` must exist in current catalog (if not found, entry is marked "unavailable" as per FR-010)
- Exactly one category per entry
- No duplicate entries allowed (liking twice triggers update, no new record)

**State Transitions:**

```
Unliked ──(heart clicked on unliked item)──> Liked
Liked ────────(heart clicked on liked item)──────────> Unliked (removed)
```

---

### FavoritesCollection

A device-scattered JSON object persisted to localStorage under key `linkschin:favorites`. Migrates from old `linkschin:watchlist` structure if present.

**Shape:**

```json
{
  "items": ["movie-id-1", "game-id-2", "music-id-3"],
  "metadata": {
    "migratedFromWatchlist": true,
    "migrationTimestamp": 1727932800000,
    "version": "2.0"
  }
}
```

**Fields:**

| Field | Type | Notes |
|-------|------|-------|
| `items` | string[] | Ordered array of `LikedItem.id`; order reflects last-modified recency |
| `metadata.migratedFromWatchlist` | boolean | True if existing watchlist entries were migrated |
| `metadata.migrationTimestamp` | number | Unix ms; set once during migration |
| `metadata.version` | string | Schema version for future migrations; default `"2.0"` |

**Constraints:**

- Maximum practical size: ~5MB localStorage quota (typically supports 1000+ ids)
- Corrupt/unreadable JSON → treat as empty (user starts fresh)
- Quota exceeded → like toggle works in-session only, no persistence

---

### MigrationMap

Defines transformation rules for migrating existing watchlist data.

| Source Key | Source Format | Destination Key | Target Format | Action |
|------------|---------------|-----------------|---------------|--------|
| `linkschin:watchlist` | `string[]` (ids) | `linkschin:favorites` | `{ items: string[], metadata: {...} }` | Copy all ids into `items`, add migration metadata |
| N/A | N/A | Delete `linkschin:watchlist` | Remove key | One-time cleanup after migration |

**Migration Logic:**

1. On app load, check for `linkschin:watchlist` in localStorage
2. If exists: parse JSON (handle errors gracefully), copy array to `favorites.items`, add migration metadata
3. After successful write, delete `linkschin:watchlist` key
4. If migration fails (corrupt watchlist): log error, start empty `favorites`, warn user in UI (FR-009)

---

## Relationships

- **FavoritesCollection** → **LikedListItem**: Many-to-one relationship via `item.id` referencing catalog entities
- **LikedItem** → **CatalogItem**: One-to-one lookup via `getCatalogItemById(id)`; if missing, item rendered as unavailable

---

## Validation & Error Handling

| Scenario | Behavior | User Feedback |
|----------|----------|---------------|
| Like an invalid ID (e.g., deleted catalog item) | Add to collection; show grayed-out card | "Unavailable" label, info tooltip |
| Corrupt localStorage JSON | Treat as empty collection; persist on next like | Non-blocking toast: "Couldn't load favorites; starting fresh" |
| Quota exceeded (no storage available) | Toggle works in-memory only; clear on session end | Info message in details view: "Likes won't persist in private mode" |
| Duplicate like (same ID twice) | Update `dateLiked`, preserve position | Instant state feedback; no extra API call |

---

## Performance Characteristics

- **Read latency**: <5ms parse + filter (typical collections <500 items)
- **Write latency**: <10ms stringify + localStorage.setItem
- **Query latency**: O(n) scan through ids to find matching catalog items (n = liked count)
- **Empty state rendering**: Immediate (<50ms)

---

## Security Considerations

- **No PII**: IDs are public catalog identifiers, never include email/address/token
- **Storage isolation**: Per-browser/device via localStorage; no server-side correlation
- **XSS boundaries**: All output escaped via React (dangerouslySetInnerHTML not used)
