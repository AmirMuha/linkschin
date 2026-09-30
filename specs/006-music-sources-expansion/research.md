# Phase 0 Research: Music Source Expansion

**Feature**: [006-music-sources-expansion](./spec.md)
**Date**: 2026-09-30
**Status**: All NEEDS CLARIFICATION items resolved

Every decision below was verified against the existing codebase before being recorded. File references are to the real state at plan time.

## R1. How is a source's `kind` represented?

**Decision**: A `SourceKind` enum (`full` | `reference`) added to `models.py` as a field on `SourceConfig`, with `SourceKind.FULL` as the default. A read-only `is_reference` property exposes the boolean that call sites actually branch on.

**Rationale**: `SourceConfig` is already a slotted dataclass carrying `id`, `name`, `category`, `base_urls`, `enabled`, `timeout_seconds` (`models.py:28`). Adding one defaulted field there is the smallest change that makes kind a first-class property of a source, which FR-002 requires. The enum beats a bare `bool` because every call site reads better as `cfg.is_reference` than as `cfg.kind == "reference"`, and a bare bool invites `"reference"` / `"ref"` / `False` drift across 20 configs.

The default is what makes this non-breaking: `SourceConfig(...)` is constructed in 6 existing places and all of them keep working untouched, satisfying FR-028.

**Alternatives considered**:
- *Separate registry list for reference sources* — rejected. It splits one registry into two and forces every consumer (`get_sources_for_category`, `/api/sources`, `SourceStatusBar`) to merge them back. More code for the same information.
- *Infer kind from category or a naming convention* — rejected, and directly forbidden by FR-021. Classification must be per-source and correctable after verification, not derived from what sort of site it is.

## R2. How is a reference source prevented from emitting media?

**Decision**: A `ReferenceSourcePlugin` base class in `sources/music/reference.py`. Its `extract_links` returns the item unchanged and is never given the machinery to populate `stream_url` or `music_tracks`. Subclasses supply only a search-URL builder and a result parser; both return `MediaItem`s with `page_url` set and media fields empty.

**Rationale**: This is the single most important design decision in the feature, because it is what makes Constitution Principle III (No Media Relaying) hold for the 9 new sources. FR-011 and FR-012 forbid reference sources from offering a player or download control and from emitting media assets. An instruction ("reference sources must not set `stream_url`") is a convention that 9 plugins × N contributors will eventually violate. A base class that has no code path producing a stream URL is a guarantee instead of a request.

It also collapses what would otherwise be 9 near-identical modules. The 9 reference sources differ only in host, search-URL shape, and card selector — exactly the variation a base class is for. This is the one new abstraction in the feature, and it has 9 implementations rather than 1, so it clears the "no interface with one implementation" bar comfortably.

**Alternatives considered**:
- *A `kind` check inside the existing search path that strips media fields* — rejected. Stripping after the fact means the code that produced the media still ran; the guarantee is cosmetic. A structural guarantee is strictly better for a NON-NEGOTIABLE principle.
- *11 full sources sharing a base class too* — rejected. Constitution Principle I requires scrapers to be decoupled plugins, and the 11 genuinely differ in markup, bitrate labelling, and artist/title extraction. Forcing them through one base would violate the isolation principle to save a little code.

## R3. Where does kind ordering happen?

**Decision**: One stable sort in `_collect_items` (`web/app.py:49`), applied to `all_items` after the `asyncio.gather` completes and before caching. The key places `full`-source items ahead of `reference`-source items and is constant within a kind, so the sort is stable and existing intra-group relevance order is untouched.

**Rationale**: `_collect_items` is the only place where full and reference results coexist — every earlier point in the function sees one category's sources at a time, and the function already owns ordering, caching, and persistence. FR-005a requires full-source results always precede reference-source results; one `list.sort` there satisfies it for both `/search` and `/api/search` simultaneously, since both call the same function.

Sorting *before* the `GLOBAL_CACHE.set` call matters: a cached response then already has the right order, so cache hits and fresh scrapes are indistinguishable to the client.

**Alternatives considered**:
- *Sort in the template / in the React component* — rejected. It would have to be reimplemented in three places (`results.html`, `_music_card.html`, and the Next.js card component), and the JSON API would return unordered results, so `/api/search` consumers would see a different order than the HTML page for the same query.
- *Sort inside each plugin* — rejected. A plugin only sees its own results and cannot know about the others.

## R4. How is the per-user hidden-source filter carried?

**Decision**: A repeated `sources` query parameter on `/search` and `/api/search`, consumed in `_collect_items` *before* `get_sources_for_category` is called. The browser holds the chosen set in local storage and appends it to every request.

**Rationale**: FR-029 asks for a per-user choice that persists across reloads with no account; FR-030 requires it to affect only that user. A query parameter is the entire server-side contract — the server holds no per-user state at all, so FR-030 is satisfied by construction rather than by enforcement, and no new table, session, or cookie is needed. Applying it before plugin selection (rather than filtering results afterwards) means a hidden source is never queried, which is the actual user intent behind "hide this source".

**Critically, the filtered set is never cached**: the `GLOBAL_CACHE` key stays `(category, normalized_query)` as it is today. Caching a filtered result set would leak one user's filter into another user's response — a real cross-user bug. This is called out explicitly in the plan because it is the one place where the feature could quietly violate FR-030.

**Alternatives considered**:
- *Cookie* — rejected. Equivalent server-side, but a cookie is sent to every request including assets, and it needs a parser plus expiry handling for no benefit here.
- *A `hidden` column on a user table* — rejected. FR-029 forbids accounts, and the spec's clarified assumption is that no account system is introduced.

## R5. How is "degraded" determined and persisted?

**Decision**: A per-source failure counter stored in the existing `crawl_state` table, which already exists with `source_id` as primary key (`db.py:66`). It gains a `consecutive_failures` column (default 0) plus a `get_failures` / `record_failure` / `record_success` API. A source is excluded from search and reported as degraded at 3 consecutive failed searches; any success resets the counter to 0.

**Rationale**: FR-018a requires the threshold be "3 separate user searches" — not 3 requests — which is exactly what incrementing once per completed search expresses. Reusing `crawl_state` is the key economy here: the table is already keyed by `source_id`, already created by the existing schema, and already has accessor functions (`get_last_page` / `set_last_page`) to model the new ones on. FR-018b's requirement that degraded state be derivable without maintainer action is satisfied because the counter moves on its own.

The existing schema is created with `CREATE TABLE IF NOT EXISTS`, so adding a column to an already-created database needs an explicit `ALTER TABLE` guarded by a check for the existing columns. This is a real implementation detail worth recording because the naive approach — editing the `CREATE TABLE` string — silently does nothing on every database that already exists.

**Alternatives considered**:
- *In-memory counter* — rejected. It resets on every server restart, so a genuinely dead source would look healthy again after any deploy, undermining SC-009.
- *A new `source_health` table* — rejected. It duplicates `crawl_state`'s primary key and adds a migration for no new information.

## R6. What does the user-facing surface need?

**Decision**: The existing Jinja templates and the Next.js components are extended, not replaced. `_music_card.html` gains a branch that renders a link-out card with no `<audio>` element when the item has no media. `SourceStatusBar.tsx` gains a kind badge and the inactive-reason text. `InViewFilterBar.tsx` gains the per-source hide toggles that persist to local storage.

**Rationale**: The codebase runs **two** frontends — the Jinja templates under `apps/api/web/templates/` and the Next.js app under `apps/web/`. `_music_card.html` already has exactly the conditional this feature needs: line 17 emits `<source src="{{ item.stream_url }}">` and line 35 renders a "no direct download link found" message when there is none. A reference-source item is precisely "an item with a page URL and no stream", so the template already knows how to render it; the work is to make the fallback state read as an intentional link-out rather than a failure.

`SourceStatusBar` already receives a `SourceStatus[]` and renders `enabled`, so FR-017's "kind + active status + reason" extends an existing prop rather than adding a new fetch.

**Alternatives considered**:
- *A separate results tab for reference sources* — rejected; the clarify session chose ordering over separation, and a tab hides the fact that these results exist at all.
- *Rendering reference results with a disabled player* — rejected, and specifically forbidden by SC-003. A control that cannot work is worse than its absence.

## R7. What are the test obligations?

**Decision**: Three new/extended test files. `test_reference_sources.py` asserts the structural invariant — that no reference plugin populates `stream_url` or `music_tracks` — across all 9. `test_source_kind.py` asserts the ordering rule, the 3-failure threshold including the reset, and the registry's 20-config shape. `test_music_scrapers.py` gains one parser test per full source against a committed fixture.

**Rationale**: Constitution Principle IV makes offline verification a hard gate, and the spec's SC-004 requires 100% of new sources to pass with no network. The reference-source invariant is the one assertion that cannot regress silently, because the failure mode it guards — a reference source quietly growing a stream URL — is invisible in review and only harmful in production.

Fixtures follow the existing `conftest.py` pattern exactly: one fixture function per HTML file under `tests/fixtures/`, read from disk and handed to the parser. No new fixture infrastructure.

**Alternatives considered**:
- *Property-based / synthetic fixtures* — rejected for full sources. The constitution requires captured *real* responses, because the whole point is to detect upstream markup the author did not anticipate.
- *Testing the invariant once on the base class* — rejected. Per-subclass assertions are what catch a subclass that overrides `extract_links`.

## Resolved unknowns

| Item | Resolution |
|---|---|
| How kind is stored | `SourceKind` enum on `SourceConfig`, defaulting to `full` (R1) |
| How media emission is prevented | `ReferenceSourcePlugin` base class with no media code path (R2) |
| Where ordering applies | One stable sort in `_collect_items` before caching (R3) |
| How the user filter is carried | Repeated query param, never cached (R4) |
| How degraded state persists | `crawl_state.consecutive_failures`, threshold 3, reset on success (R5) |
| Frontend surface | Extend both existing frontends; no replacement (R6) |
| Test shape | Three files following the existing fixture pattern (R7) |

No NEEDS CLARIFICATION items remain open.
