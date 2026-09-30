# Data Model: Movie Source Expansion

**Feature**: `005-movie-source-expansion` | **Date**: 2026-09-30

## Existing model being extended

Four entities already exist and are modified, not replaced. New entities are additions.

## `MediaItem` — modified

A discovered title. One field added.

| Field | Type | Change | Notes |
|---|---|---|---|
| `id` | str | existing | |
| `title_fa` | str | existing | |
| `title_en` | str | existing | |
| `category` | Category | existing | No new category value added (per clarification Q1) |
| `year` | int \| None | existing | |
| `poster_url` | str | existing | |
| `description` | str | existing | |
| `source_id` | str | existing | |
| `source_name` | str | existing | |
| `stream_url` | str \| None | existing | A **playable direct file** URL. Unchanged meaning. |
| **`watch_url`** | **str \| None** | **NEW** | A **watch-page** URL on a subscription source. Never a download. |
| `movie_variants` | list[MovieDownloadVariant] | existing | Empty for watch-only items |

### Field rules

- `watch_url` and `stream_url` are **distinct concepts and must not share a column**:
  - `stream_url` = a direct media file that may be played in-browser after CORS validation
  - `watch_url` = a page on the source's own domain where a subscription/member may watch
- A watch-only item MUST have `watch_url` set and `movie_variants` empty.
- A download item MUST have `movie_variants` non-empty. Setting `watch_url` on it is permitted only
  if the site also publishes a watch page, and it never replaces the variants.
- An item with neither is invalid and MUST be discarded before return (FR-017, FR-018).
- `watch_url` MUST pass the existing `validate_media_url` scheme/netloc validation so only absolute
  `http`/`https` values are stored.

## `SourceConfig` — semantics extended, shape unchanged

| Field | Type | Change | Notes |
|---|---|---|---|
| `id` | str | existing | Stable key for health tracking |
| `name` | str | existing | |
| `category` | Category | existing | |
| `base_urls` | list[str] | **semantics change** | Was "first element is the base". Now "ordered list: primary first, fallbacks after" (FR-012a) |
| `enabled` | bool | existing | Read at startup, not runtime (clarification Q3) |
| `timeout_seconds` | float | existing | 7.0 default |
| **`provides_downloads`** | **bool** | **NEW** | False for subscription/watch-only sources (FR-003) |
| **`inactive_reason`** | **str \| None** | **NEW** | Plain-language reason shown to consumers (FR-009) |
| **`last_reachable_at`** | **datetime \| None** | **NEW** | Date the source last returned results (FR-009b) |

`primary_base_url` (property, returns `base_urls[0]`) is retained unchanged — existing callers keep
working. New fallback behaviour reads the whole list.

## `SourceHealth` — new entity

Per-source operational state, keyed by `source_id`. Backs FR-008, FR-009, FR-019, FR-020.

| Field | Type | Notes |
|---|---|---|
| `source_id` | str | Primary key. Matches `SourceConfig.id` |
| `state` | SourceState | One of the five states below |
| `reason` | str \| None | Plain-language, consumer-facing |
| `last_success_at` | datetime \| None | |
| `last_failure_at` | datetime \| None | |
| `consecutive_failures` | int | Drives the circuit breaker |
| `active_address` | str \| None | Which address last served a request (FR-012a) |

### `SourceState` — state machine

```
                  ┌──────────────────────────────┐
                  ▼                              │
   [unregistered] ──register──▶ PROVIDING_RESULTS ─┤
                                  │  │  │         │ 0 results while HTTP 200
                    fails        │  │  │ recovers│ (silent break, FR-019)
                    ┌───────────┘  │  └─────────┘
                    ▼              ▼
              UNREACHABLE ◀── SUBSCRIPTION_ONLY
                    │              │
                    │ recovers     │ (static: never flips on its own)
                    └──────────────┘
                                      
   any state ──interactive challenge──▶ REQUIRES_LOGIN ──▶ (terminal; not scraped)
   
   any state ──first evaluation, never proven──▶ NOT_YET_PROVEN
```

| State | Meaning | In search? | In listing? |
|---|---|---|---|
| `PROVIDING_RESULTS` | Returns results | Yes, active | Yes, normal |
| `SUBSCRIPTION_ONLY` | Watch destination only, no public links | Yes, as watch-only | Yes, labelled |
| `UNREACHABLE` | All configured addresses failed | No | Yes, **greyed out** (clarification Q2) |
| `REQUIRES_LOGIN` | Bot wall or interactive sign-in | No | Yes, greyed out, with reason |
| `NOT_YET_PROVEN` | Registered but never returned a result | No | Yes, greyed out |

### State rules

- `UNREACHABLE` → `PROVIDING_RESULTS` happens **automatically** on the first successful response.
  No manual intervention (FR-009c, SC-001a).
- `REQUIRES_LOGIN` is **sticky**. The platform does not attempt interactive sign-in (R-007), so a
  source that hits a bot wall must not be retried on every search.
- `SUBSCRIPTION_ONLY` is a static property of the site, not a failure. It is not a health fault and
  must not count toward `consecutive_failures`.
- A source that returns HTTP 200 but parses to zero items increments `consecutive_failures` and
  eventually reports as degraded — this is the FR-019 signal, and it is the whole reason state is
  persisted rather than derived from a single response.

## `SourceProfile` — new declarative config shape

Replaces the "standard site pattern engine" from FR-022 (see plan.md Complexity Tracking). Read from
a hand-written configuration file at startup (clarification Q3).

| Field | Type | Notes |
|---|---|---|
| `id` | str | |
| `name` | str | |
| `category` | Category | |
| `addresses` | list[str] | Ordered: primary, then fallbacks. Validated on load (FR-014) |
| `provides_downloads` | bool | False ⇒ watch-only |
| `parser` | str | Name of the parser that handles this site's shape |
| `enabled` | bool | |

### Validation rules

- Every address MUST be an absolute `http`/`https` URL with a netloc. Invalid entries are rejected
  at load with the source id and the offending value (FR-014); they MUST NOT be silently dropped.
- The first address is the primary; the rest are fallbacks tried in order (FR-012a).
- `parser` MUST name a registered parser. An unknown parser name is a load error, not a silent
  no-op (FR-023).

## Relationships

```
SourceConfig 1 ──▶ 0..1 SourceHealth        (keyed by source_id)
SourceConfig 1 ──▶ *   MediaItem            (via source_id)
MediaItem    1 ──▶ *   MovieDownloadVariant (empty when watch-only)
MediaItem    1 ──▶ 0..1 watch_url          (subscription sources only)
SourceProfile 1 ──▶ 1  parser               (many profiles may share one parser)
```

## Persistence

- `MediaItem.watch_url` — new column in the `items` table; `db.upsert_items` and `db._rehydrate` must
  round-trip it or watch-only items lose their destination on first cache read (R-005).
- `SourceHealth` — new table, following the existing `db.get_last_page` / `db.set_last_page`
  per-source-state pattern (R-004).
- In-memory TTL cache is unchanged and keyed by category + normalized query, so the new sources
  participate in existing caching with no change.
