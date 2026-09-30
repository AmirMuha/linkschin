# Bug Fix: Games results include music posts; search term persists across tabs

- **Slug**: search-tab-bugs
- **Fixed**: 2026-09-30
- **Assessment**: ./assessment.md
- **Status**: applied

## Summary

A games search now returns only game posts: the Downloadha scraper gates each card on the
URL section that proves it is a game, and `_collect_items` filters plugin output by the
requested category so a soundtrack can never reach the games tab. Switching tabs clears
the search input and no longer re-runs the previous term.

## Changes

| File | Change | Notes |
|------|--------|-------|
| `apps/api/sources/base.py` | modified | Hoisted `classify_post` here from `downloadha.py` so both games plugins share one gate; added `is_game_post(title, url)` (URL-section gate) |
| `apps/api/sources/games/downloadha.py` | modified | `parse_search_results` applies `is_game_post` before emitting a `Category.GAMES` item |
| `apps/api/sources/games/yasdl.py` | modified | `parse_search_results` drops non-game posts via the shared `classify_post` |
| `apps/api/web/app.py` | modified | `_collect_items` persists the whole scrape, then filters the response by the requested category |
| `apps/api/db.py` | modified | `schema_meta` table + marker-guarded one-time DELETE of misfiled Downloadha game rows |
| `apps/web/src/app/page.tsx` | modified | `handleCategoryChange` adds `setQuery('')`, drops the auto-re-search block |
| `apps/api/tests/test_games_scrapers.py` | modified | Replaced the assertions that pinned the bug; added 4 new tests |
| `apps/api/tests/test_db.py` | modified | Added `test_migration_drops_misfiled_game_rows_once` |
| `e2e/specs/001-mvp/search-tab-bugs.spec.ts` | added | Tab-switch regression spec |

`SearchBar.tsx` was left unchanged, as the assessment specified — it is fully controlled
and derives its clear/refresh/disabled states from `query`.

## Diff Highlights

The gate that actually fixes the report. A title marker cannot work here: the offending
post is titled `دانلود موسیقی متن بازی GTA Online Arena War` and so *contains* بازی.

```python
# apps/api/sources/base.py
def is_game_post(title: str, post_url: str) -> bool:
    if classify_post(title) != "game":
        return False
    sections = [p for p in urlparse(post_url).path.split("/") if p]
    section = sections[0].lower() if sections else ""
    if section == "game":
        return True
    return section == "mobile" and "بازی" in title
```

```python
# apps/api/web/app.py — the one guard that covers every caller.
# Order matters: persist first, filter second. The index is the only way a
# re-labelled item (a soundtrack) becomes searchable again, so filtering
# before the upsert would make every soundtrack permanently unfindable.
if all_items:
    db.upsert_items(all_items)
    matching = [i for i in all_items if i.category == cat_enum]
    if not matching:
        return [], warnings, False
    GLOBAL_CACHE.set(cat_enum, norm_query, matching)
    return matching, warnings, False
```

```tsx
// apps/web/src/app/page.tsx
setFilters({ qualities: [], audioTracks: [], sources: [] })
// Each tab is a fresh query: the old term is about a different category, and
// re-running it fired a search from the pre-switch handleSearch closure.
setQuery('')
```

## Tests Added or Updated

- `test_games_scrapers.py::test_downloadha_keeps_only_posts_the_url_calls_games` — the
  invariant: every post *filed as a game* sits in `/game/`, or `/mobile/` with بازی; GTA OST
  and GTasks are not filed as games.
- `test_games_scrapers.py::test_downloadha_keeps_android_games_filed_under_mobile` — pins
  the `/mobile/` carve-out so a stricter gate cannot silently drop Android games.
- `test_games_scrapers.py::test_downloadha_keeps_games_whose_titles_collide_with_software_terms`
  — over-filtering guard; see Deviations.
- `test_games_scrapers.py::test_yasdl_keeps_only_game_posts` — synthetic mixed-section
  YasDL markup, asserting only the game survives.
- `test_api_search.py::test_games_response_excludes_music_but_still_indexes_it` — pins both
  halves of the `_collect_items` change: the games response carries only the game, and the
  soundtrack is still persisted so the music tab can find it. (Added during
  `/speckit-bug-test`; see Deviations.)
- `test_games_scrapers.py::test_downloadha_search_parsing` — rewritten: 8 games + 1
  soundtrack, replacing the `len == 9` assertion that pinned the bug.
- `test_games_scrapers.py::test_downloadha_routes_soundtracks_to_music` — rewritten from a
  fixture-scoped assertion to a standalone unit test, since the soundtrack is no longer in
  the games fixture's game output.
- `test_db.py::test_migration_drops_misfiled_game_rows_once` — seeds a misfiled row, a
  `/game/` row, a `/mobile/` row and a YasDL row; asserts only the misfiled one goes, that
  its `game_parts` and FTS entry follow, that the marker is set, and that a second connect
  is a no-op.
- `e2e/specs/001-mvp/search-tab-bugs.spec.ts` — types a term in Movies, switches to Games,
  asserts the input is empty and no `/api/search` was issued.

## Local Verification

- `apps/api: pytest tests/ -q` → **73 passed, 1 deselected**. The deselected test is
  `test_movies_scrapers.py::test_parse_quality_reads_positional_cdn_names`, which fails on
  this branch **before and after** this fix and is unrelated to it (see Follow-ups).
- `e2e: npx playwright test search-tab-bugs --project=hermetic-chromium` → **1 passed**.
  Verified to be a real guard: with `setQuery('')` temporarily removed the spec **fails** on
  the `toHaveValue('')` assertion, and passes again once restored.
- `apps/web: npx tsc --noEmit` → no error in `page.tsx`. One pre-existing unrelated error
  remains in `src/lib/archive.test.ts` (a `.ts` import extension), untouched by this fix.
- Manual: none — both bugs are covered by the automated checks above.

## Deviations from Assessment

1. **Non-game posts are relabelled as MUSIC, not dropped.** The assessment preferred
   "the games plugin returns games only". The working tree already carried in-flight,
   uncommitted work on `dev` doing the opposite — `classify_post` routing soundtracks to
   `Category.MUSIC`, plus `parse_bitrate` and a music branch in `parse_item_page` that
   make Downloadha soundtracks play. This was confirmed with the user before proceeding:
   keep that work, and fix the report by keeping the music out of the *games tab*. So
   soundtracks are still emitted (labelled MUSIC) and still indexed, and `_collect_items`
   is what filters them out of the games response. Dropping them entirely would have
   deleted working, uncommitted functionality.

2. **A third root cause the assessment did not identify: `_collect_items`.** The assessment
   scoped the fix to the scrapers, on the reasoning that category plumbing was "verified
   correct and NOT to blame". But a games plugin emitting a `Category.MUSIC` item is enough
   on its own — the fresh-scrape path returns plugin output **unfiltered**, while the cache
   and the DB both filter by stored category. So the fresh-scrape path was the single route
   that could put a music post in the games tab, independent of any URL gate. Fixed in
   `_collect_items` so every caller and every item source is covered in one place.

3. **The cleanup DELETE is scoped to `downloadha` only.** The assessment's SQL used
   `source_id IN ('downloadha','yasdl')`, which would have **deleted every YasDL row**:
   YasDL permalinks are flat (`/105441/دانلود-بازی…`) with no section segment, so
   `page_url NOT LIKE '%/game/%'` is true for 100% of them. The assessment flagged the
   YasDL section convention as its one thin-evidence area, and the fixture confirms it.

4. **`شبیه ساز` narrowed in `_SOFTWARE_TERMS`.** `شبیه ساز` ("simulator") is a substring of
   `بازی شبیه ساز` ("simulation game"), which titles Euro Truck Simulator 2 in the YasDL
   fixture. Gating YasDL on `classify_post` dropped it, turning a latent defect into a
   visible regression. Replaced with the two phrasings the actual emulator posts use
   (`شبیه ساز اندروید`, `اندروید شبیه ساز`). `test_downloadha_keeps_games_whose_titles_collide_with_software_terms`
   pins this. An earlier attempt at a broader `^دانلود\s+(?!بازی\b)` title rule was
   reverted: it also dropped a legitimate `/game/` PS5 game post.

5. **The soundtrack bitrate test's fixture URL changed** from `/others/ost/` to
   `/movies/ost-spider-man/`, since the section gate now applies to that path.

6. **Corrected during `/speckit-bug-test`.** This report originally claimed the music tab
   can serve Downloadha soundtracks. It could not: `_collect_items` filtered *before*
   `db.upsert_items`, so a soundtrack was dropped without ever being written to the index,
   and the only route to a re-labelled item is the index. The filter now runs after the
   upsert. `test_api_search.py::test_games_response_excludes_music_but_still_indexes_it`
   pins both halves, and was confirmed to fail on the old ordering.

## Follow-ups

- `test_movies_scrapers.py::test_parse_quality_reads_positional_cdn_names` is failing on
  `dev` and is **not** from this fix. `QUALITY_RE` in `apps/api/sources/base.py:88` uses
  `(?<!\d)`, so `Batman_2026_720p_UPTV.co.mp4` (an underscore before the resolution) does
  not match and `parse_quality` returns `""`. Someone's in-flight work moved `parse_quality`
  into `base.py` and left this case behind.
- `apps/web/src/lib/archive.test.ts` has a pre-existing `tsc` error (a `.ts` import
  extension needing `allowImportingTsExtensions`). Untouched here.
- The in-memory TTL cache (45 min, `cache.py`) can still serve pre-fix results right after
  deploy; it self-heals. The DB cleanup handles the persistent half immediately.
- Per the assessment: `SPECIFY_FEATURE=006-music-sources-expansion` is stale in the
  environment and misdirects Spec Kit resolvers; unset it before `/speckit-plan`.
- Now that Downloadha soundtracks are indexed as `category='music'`, the Music tab can
  serve them. Worth confirming the MusicCard UI renders the bitrate variants the
  `parse_item_page` music branch populates.
