# API Contract: Source Expansion

- **Feature**: `005-movie-source-expansion`
- **Host**: `apps/api` (FastAPI at `http://localhost:8000`)
- **Consumer**: `apps/web` (Next.js at `http://localhost:3000`)

Field names below match the current `MediaItem` dataclass in `apps/api/models.py` exactly
(`title`, `original_title`, `release_year`, `page_url`, `source_id`, `stream_url`).

---

## 1. `GET /api/search` — modified

Unchanged signature. One field added to each item.

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | Yes | - | Search query (Persian or English) |
| `category` | string | No | `"movies"` | `movies`, `games`, or `music`. **No new value** (clarification Q1) |
| `refresh` | boolean | No | `false` | Bypass in-memory cache and SQLite |

### Response — added field

```json
{
  "query": "Inception",
  "category": "movies",
  "is_cached": false,
  "warnings": [
    "منبع Tiwall در دسترس نیست (آخرین بار: ۱۴۰۴/۰۷/۰۸)."
  ],
  "items": [
    {
      "id": "movies-inception-2010-namava",
      "title": "تلقین (Inception)",
      "original_title": "Inception",
      "category": "movies",
      "source_id": "namava",
      "page_url": "https://namava.ir/movie/inception",
      "release_year": 2010,
      "poster_url": "https://.../poster.jpg",
      "description": "...",
      "stream_url": null,
      "watch_url": "https://namava.ir/movie/inception",
      "movie_variants": []
    }
  ]
}
```

### `watch_url` — new field

| Aspect | Rule |
|---|---|
| Type | `string \| null` |
| Meaning | A **watch page** on the source's own site. Distinct from `stream_url`, which is a playable direct file. |
| Present on | Subscription sources (Filimo, Namava, Filmnet, Namasha, Tiwall, Salam Cinema) |
| Absent/`null` on | Download sources, unless the site also publishes a watch page |
| Never | A direct file, a CDN URL, or anything the platform unlocks |
| Validation | Absolute `http`/`https` only, via the existing `validate_media_url` |

### Invariants

1. A watch-only item MUST have `watch_url` non-null and `movie_variants` empty.
2. An item MUST have `watch_url` or a non-empty `movie_variants`. An item with neither is discarded
   before the response is built (FR-017, FR-018).
3. **No item for a gated title may ever carry a populated `movie_variants`** (FR-006, SC-007).
4. `category` gains no new value; all 20 sites are searched under `movies` (FR-004).

---

## 2. `GET /api/sources` — modified

Was `[{id, name, category, base_url, enabled}]`. Each entry gains the state fields so the web client
can render greyed-out inactive sources (FR-009a, FR-009b, clarification Q2).

```json
[
  {
    "id": "namava",
    "name": "Namava",
    "category": "movies",
    "base_url": "https://namava.ir",
    "enabled": true,
    "provides_downloads": false,
    "state": "subscription_only",
    "inactive_reason": "سرویس اشتراکی — بدون لینک دانلود عمومی",
    "last_reachable_at": "2026-09-30T11:20:04Z",
    "active_address": null
  },
  {
    "id": "tiwall",
    "name": "Tiwall",
    "category": "movies",
    "base_url": "https://tiwall.com",
    "enabled": true,
    "provides_downloads": false,
    "state": "unreachable",
    "inactive_reason": "دامنه پاسخ نمی‌دهد (آخرین دسترسی موفق: ۱۴۰۴/۰۶/۲۳)",
    "last_reachable_at": null,
    "active_address": null
  }
]
```

### `state` — new field

One of: `providing_results`, `subscription_only`, `unreachable`, `requires_login`, `not_yet_proven`.

| Field | Type | Notes |
|---|---|---|
| `provides_downloads` | boolean | False ⇒ this source never returns `movie_variants` |
| `state` | enum | See data-model.md state machine |
| `inactive_reason` | string \| null | Plain-language, consumer-facing (FR-009) |
| `last_reachable_at` | ISO-8601 \| null | When it last returned results (FR-009b) |
| `active_address` | string \| null | Which configured address last served a request (FR-012a) |

### Invariants

1. **Every registered source appears**, including unreachable ones. Absence is never used to
   represent a dead source (FR-009a, SC-001).
2. `base_url` remains the primary address; fallbacks are not serialised to keep the response stable.
3. A source with `state: "unreachable"` renders greyed out in the client and is excluded from search.

---

## 3. `GET /api/health` — modified

Adds a per-source health summary. Existing keys (`status`, `version`, `cache_entries`,
`registered_sources`, `database_stats`) are unchanged.

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "cache_entries": 14,
  "registered_sources": { "movies": [], "games": [], "music": [] },
  "database_stats": { },
  "source_health": [
    { "source_id": "babakfilm", "state": "providing_results", "consecutive_failures": 0,
      "last_success_at": "2026-09-30T11:20:04Z" },
    { "source_id": "filmchiin", "state": "providing_results", "consecutive_failures": 3,
      "last_success_at": "2026-09-30T09:02:11Z" }
  ],
  "source_health_counts": {
    "providing_results": 14,
    "subscription_only": 6,
    "unreachable": 3,
    "requires_login": 0,
    "not_yet_proven": 0
  }
}
```

The `consecutive_failures` counter is what surfaces the FR-019 silent break: a source returning
HTTP 200 with nothing parseable accumulates failures here while a source that legitimately has no
matching titles does not.

---

## 4. Declarative site profile file — new

Read once at startup (clarification Q3 — no admin screen). Replaces the general pattern engine
with a site profile; see plan.md Complexity Tracking.

```yaml
# apps/api/sources/profiles.yaml
sources:
  - id: babakfilm
    name: BabakFilm
    category: movies
    provides_downloads: true
    parser: html_wordpress_list
    addresses:
      - https://babakfilm.com
      - http://babakfilm.com

  - id: namava
    name: Namava
    category: movies
    provides_downloads: false      # subscription; watch destination only
    parser: html_search_card
    addresses:
      - https://namava.ir
```

### Load-time validation (FR-014, FR-023)

| Rule | On violation |
|---|---|
| Every `addresses` entry is an absolute `http`/`https` URL with a netloc | Reject the entry and report the source id + offending value. Do not silently drop. |
| `addresses` is non-empty | Reject the source |
| `parser` names a registered parser | Reject the source and report the unknown name — never register a source that silently returns nothing |
| `category` is a known value | Reject the source |

---

## 5. Web client changes

### `apps/web/src/types/media.ts`

```ts
export type SourceState =
  | 'providing_results'
  | 'subscription_only'
  | 'unreachable'
  | 'requires_login'
  | 'not_yet_proven'

export interface SourceInfo {
  id: string
  name: string
  category: Category
  base_url: string
  enabled: boolean
  provides_downloads: boolean
  state: SourceState
  inactive_reason: string | null
  last_reachable_at: string | null
  active_address: string | null
}
```

`Category` is **unchanged** — still `'movies' | 'games' | 'music'`.

### `MovieCard.tsx`

- If `watch_url` is set and `movie_variants` is empty → render a **watch** action, no download button.
- If `movie_variants` is non-empty → render download actions; show `watch_url` as a secondary link if present.
- The two action kinds MUST be visually distinct (FR-017).

### `SourceStatusBar.tsx`

- Renders every source from `/api/sources`, including inactive ones.
- `state !== 'providing_results'` → greyed out with `inactive_reason` and `last_reachable_at`.

### Streaming toggle (FR-005)

- A control within the Movies tab switching between downloads-only (default) and all sources
  including watch-only entries.
- **No new tab is added.**
