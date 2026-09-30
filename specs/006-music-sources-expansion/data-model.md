# Data Model: Music Source Expansion

**Feature**: [006-music-sources-expansion](./spec.md) | **Date**: 2026-09-30

## New types

### SourceKind

| Field | Type | Notes |
|---|---|---|
| `FULL` | `str` enum, value `"full"` | Resolves to playable + downloadable media |
| `REFERENCE` | `str` enum, value `"reference"` | Resolves to a page link only; never emits media |

Added to `apps/api/models.py` alongside the existing `Category` enum, which it mirrors in style (`class Category(str, Enum)`).

**Validation rule**: the value is set by configuration only. There is no user input path into it, so no runtime validation is required.

### SourceConfig (modified)

Existing fields are unchanged. One field is added:

| Field | Type | Default | Notes |
|---|---|---|---|
| `kind` | `SourceKind` | `SourceKind.FULL` | Set per source in the registry |

**Read-only helper**: `is_reference -> bool`, returning `self.kind is SourceKind.REFERENCE`. Branch on this rather than comparing to the enum, so call sites read as intent.

**Compatibility**: the default is `SourceKind.FULL`, so all 6 existing `SourceConfig(...)` construction sites keep working unchanged. This is what keeps FR-028 true — the movies, games, and already-supported music sources are untouched by this field's addition.

## Modified persistence

### crawl_state (existing table, extended)

The table already exists (`db.py:66`) keyed by `source_id`. One column is added:

| Column | Type | Default | Notes |
|---|---|---|---|
| `consecutive_failures` | `INTEGER` | `0` | Failed searches since the last success |

Existing columns (`source_id`, `last_page`, `last_crawl`) are untouched, so `get_last_page` / `set_last_page` keep working unchanged.

**Migration requirement**: the schema is created with `CREATE TABLE IF NOT EXISTS`, so editing that string has no effect on any database that already exists. The column must be added via `ALTER TABLE ... ADD COLUMN`, guarded by a check of `PRAGMA table_info(crawl_state)` so the migration is idempotent across both fresh and pre-existing databases. This is a genuine implementation trap and is called out so it is not missed.

**New accessors**, modelled on the existing `get_last_page` / `set_last_page` pair:

| Function | Behaviour |
|---|---|
| `get_consecutive_failures(source_id) -> int` | Returns the counter, `0` if the source has no row |
| `record_search_failure(source_id) -> int` | Increments, returns the new value |
| `record_search_success(source_id) -> None` | Resets to `0` |

## Derived state (not stored)

### Source health

Health is derived from `consecutive_failures` rather than stored separately, so the two can never disagree:

| Condition | Reported status | Queried in search? |
|---|---|---|
| `consecutive_failures < 3` | `active` | yes |
| `consecutive_failures >= 3` | `degraded` | no — excluded |
| `enabled = false` in config | `inactive` + `reason` | no |

**State transitions** (per FR-018a, clarified to 3 *separate searches*, not 3 requests in a row):

```text
              failure                      failure
   active ─────────────────► active ─────────────────► degraded
      ▲                        (1)      (2)                │
      │                                                    │
      └────────────── success ─────────────────────────────┘
                  (any success resets the counter to 0)
```

A single failure never changes a displayed status, which is what keeps a momentary outage from flickering a healthy source off the list.

### Inactive reason

`SourceConfig` gains no new field for this. The reason is supplied by a module-level mapping from source id to a short human-readable string, defined beside the registry in `sources/__init__.py`. A source with no entry in that mapping and `enabled = false` reports a generic fallback.

This is deliberately not a dataclass field: a reason is display text for a handful of disabled entries, and adding a field to `SourceConfig` that only some instances populate would be a wider change than the problem needs.

## New entity: reference source result

Reference sources reuse `MediaItem` and emit **no** new type. A reference result is characterized by:

| Field | Value |
|---|---|
| `page_url` | the track's page on the originating site — set |
| `stream_url` | `None` |
| `music_tracks` | `[]` |
| `source_id` | the reference source's id |

**This is the whole modelling trick.** The spec's assumption that "a reference source's track is distinguished by the presence or absence of media fields, not by a new model" holds because `MediaItem` already types all three as optional. No new media kind, no subclass, no discriminator column on `MediaItem`.

The consequence worth stating: nothing in the data model *prevents* a reference item from carrying a stream URL. That guarantee is structural at the plugin layer (`ReferenceSourcePlugin` has no code path that sets one) and is asserted by test, not by the schema. The spec's SC-008 and the constitution's Principle III are upheld by that pairing.

## Result ordering

Applied in `_collect_items` after the gather, before caching:

| Position | Items | Key |
|---|---|---|
| First | All full-source items | `0` |
| Last | All reference-source items | `1` |

The sort is stable and the key is constant within a kind, so the pre-existing relevance order inside each group is preserved exactly (FR-005a).

## Registry shape

`DEFAULT_CONFIGS` grows from 12 entries to 31: the existing 12 (movies, games, and the 2 live music sources) plus 19 new music entries. Nex1Music is counted among the 11 full sources but is **not** a new entry — it is the existing `nex1music` entry reconciled below, so 10 new full + 1 reconciled = 11 full. Every new entry sets `kind` explicitly rather than relying on the default, so the full/reference split is readable at the point of declaration.

| Kind | Count | Source ids |
|---|---|---|
| `full` | 11 | `radiojavan`, `musicdel`, `nex1music` (reconciled, not new), `musicfa`, `upsong`, `upmusics`, `musictarin`, `tehranmusic`, `melodify`, `takmusics`, `one_rj` |
| `reference` | 9 | `shenoto`, `farsichart`, `aparat`, `namasha`, `rubika`, `fam`, `soundcloud`, `spotify`, `youtube_music` |

**Reconciliation (FR-024)**: two of these names already exist in the registry and must be updated rather than duplicated.

| Existing | Problem | Resolution |
|---|---|---|
| `nex1music` (enabled, `nex1music.com`) | the request names `nex1music.ir` | Reconcile to one entry carrying both domains in `base_urls`; do not add a second entry. The `.com` domain is the one currently verified working. |
| `radiojavan` (disabled, no reason) | the request names it as a supported site | Update in place to the confirmed domain and set its real status. Do not add a second entry. |

`get_sources_for_category` gains a `exclude_ids` parameter used for the per-user filter (FR-029). It defaults to empty, so every existing caller is unaffected.

## Validation rules

| Rule | Source |
|---|---|
| A source's `kind` is configuration-only, never user input | FR-002 |
| A reference result MUST have `stream_url is None` and `music_tracks == []` | FR-011 |
| No reference plugin may be constructed with credentials or tokens | FR-012 |
| A source at 3+ consecutive failures MUST be excluded from search | FR-018a |
| A user's hidden set MUST NOT suppress a system-determined inactive/degraded state | FR-031 |
| Every registered source MUST appear in `/api/sources` with kind and status | FR-017 |
