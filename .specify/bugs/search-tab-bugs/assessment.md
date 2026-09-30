# Bug Assessment: Games results include music/mobile posts; search term persists across tabs

- **Slug**: search-tab-bugs
- **Created**: 2026-09-30
- **Source**: pasted text (user report via `/speckit.bug.assess`, 2026-09-30 session); full
  evidence trail in `.specify/assessments/search-tab-bugs/{intake,research,clarifications}.md`
- **Verdict**: valid — both bugs reproduced from source and the repo's own fixture
- **Severity**: high (Bug 1), medium (Bug 2)

## Report (verbatim)

> I have found two blocks in the application one because I've been researched for a game and
> the results you have also some music videos for that game too and I need the platform, I
> need the application to only show the games, not the music video of those games that was
> first part and the second part is when changing tabs from movies to games or to music or
> vice versa the application should clear the search input for a new set of instructions or
> search input Oh search term.

## Symptom

1. Searching the Games tab for a game returns results that are not games — e.g. a music/OST
   post for the same game — because the games scrapers label every search-page card as
   `Category.GAMES`.
2. Switching tabs (Movies ↔ Games ↔ Music) keeps the previous search term in the input and
   silently re-runs it in the new category; the user expects an empty search box per tab.

## Reproduction

Bug 1 (deterministic, no live site needed):
1. `cd apps/api && pytest tests/test_games_scrapers.py::test_downloadha_search_parsing` —
   passes today *because it asserts the music item is correct output*.
2. Run the parser over `tests/fixtures/downloadha_search.html` (command recorded in
   `research.md`): 10 cards returned, including `دانلود موسیقی متن بازی GTA Online Arena
   War` (`/others/`) and `دانلود GTasks ...` (`/mobile/`), all stamped `category=GAMES`.

Bug 2:
1. `pnpm dev` (web), type a query in Movies, switch to Games — input still holds the term
   and a search fires automatically against Games.

## Suspected Code Paths (confirmed)

- `apps/api/sources/games/downloadha.py:68-100` — `parse_search_results` regex matches every
  `entry-title` heading on the multi-section search page; `Category.GAMES` hardcoded per card,
  no content-type gate. **Root cause of Bug 1.**
- `apps/api/sources/games/yasdl.py:68-99` — identical unscoped pattern (`post-title` cards,
  hardcoded GAMES). Latent (no mixed-section fixture), same defect.
- `apps/api/tests/test_games_scrapers.py:9-12` — asserts `len(items) == 10` and
  `"GTA Online Arena War" in first.title`: the test **pins the bug**.
- `apps/web/src/app/page.tsx:124-139` — `handleCategoryChange` resets items/warnings/
  hasSearched/error/filters but never `setQuery('')`, and re-runs the stale query via
  `setTimeout(() => handleSearch(query.trim()), 0)`. **Root cause of Bug 2.**
- `apps/web/src/app/page.tsx:21-22, 246` + `SearchBar.tsx:109` — `query` lives only in
  `Home`; `SearchBar` is fully controlled. Clearing `query` suffices; no SearchBar change.
- Category plumbing verified correct and NOT to blame (do not fix here): `api.ts` param →
  `web/app.py:178-202` enum parse → `_collect_items` plugin selection
  (`sources/__init__.py:140-164`) → `cache.py:66-68` key `f"{cat}:{norm_q}"` → `db.py:234-262`
  `m.category = ?`.
- Persistence path that keeps Bug 1 alive after the fix: `web/app.py:115` →
  `db.upsert_items` (`db.py:119`, upsert by id). Rows scraped before the fix keep
  `category='games'` forever — the fixed scraper never re-emits them to overwrite, and DB
  search filters the stored category.

## Root Cause Hypothesis

**High confidence, verified end to end.** Bug 1: Downloadha is a multi-section WordPress site
(`/game/`, `/mobile/`, `/others/`, `/movies/`) whose search page mixes sections; the scraper
is section-blind and stamps GAMES on everything it matches. The item is born mislabeled and
served faithfully downstream (UI, cache, DB all filter correctly by the stored label). Bug 2:
`handleCategoryChange` intentionally re-searches the stale term (comment: "If query already
entered, immediately execute search in new category") and omits the `setQuery('')` reset; the
`setTimeout` also captures the pre-switch `handleSearch` closure (`useCallback` dep
`[category]`), a stale-category race removed for free when the block is deleted.

## Proposed Remediation

**Preferred (Bug 1)** — gate `DownloadhaPlugin.parse_search_results` (and the identical
pattern in `yasdl.py`) with the predicate validated in `clarifications.md`, in order:
1. title contains a music word (`موسیقی`, `موزیک`, `آلبوم`, `soundtrack`, case-insensitive)
   → drop. Do **not** include bare `ost` — it matches "All C**ost**s" and drops real games.
2. URL section == `game` → keep.
3. URL section == `mobile` AND title contains `بازی` → keep (Android games live under
   `/mobile/` on this site).
4. otherwise → drop (GTA `/others/` OST and GTasks `/mobile/` app are rejected here).

Rejected the title-marker-only approach outright: the offending music post's title *contains*
the game marker (it is music *about* a game), so no marker-based gate fixes the reported
symptom — only URL section does. Rejected re-labeling rejects as MUSIC: the games plugin
returns games only; excluded items are dropped entirely.

**Preferred (Bug 1 follow-through)** — one-time cleanup of already-persisted mislabeled rows,
run automatically once at startup (user-confirmed): a marker-guarded DELETE scoped to the
games sources, e.g.

```sql
DELETE FROM media_items
WHERE source_id IN ('downloadha','yasdl') AND category='games'
  AND page_url NOT LIKE '%/game/%'
  AND NOT (page_url LIKE '%/mobile/%' AND title LIKE '%بازی%');
```

Anchor: `db.connect()` (`db.py:79-89`) already runs `executescript(SCHEMA)` on every call —
add a `schema_meta`/`crawl_state` marker check there or at app construction
(`web/app.py:27`), so it executes exactly once and is idempotent across restarts. The DELETE
must respect the existing FTS trigger (`db.py:73-74`: `trg_fts_delete` fires on
`media_items` DELETE, so FTS stays consistent automatically; `download_variants`/`game_parts`
cascade via `ON DELETE CASCADE`).

**Preferred (Bug 2)** — in `handleCategoryChange`: add `setQuery('')` and delete the
`if (query.trim()) { setTimeout(...) }` block entirely. Tab switch yields an empty, idle
search box; the stale-closure race disappears with it. `SearchBar.tsx` unchanged (clear/
refresh/disabled states already derive from `query`). Recent-search chips
(`addRecentSearch`, `lib/history.ts`) left as-is — cross-category shortcuts by design
(user-confirmed).

**Alternatives**
- Read-time DB guard instead of DELETE: keeps junk rows, complicates every query; rejected —
  fix-at-source once is smaller total code.
- Nuke the DB file: loses correct rows for all categories; rejected.
- Keep auto-search on tab switch with fixed closure: contradicts the explicit request for a
  cleared input; rejected.

**Files likely to change**
- `apps/api/sources/games/downloadha.py` (gate in `parse_search_results`)
- `apps/api/sources/games/yasdl.py` (same gate, adapted to its URL shapes — verify its
  section convention before copying `/game/` blindly)
- `apps/api/db.py` (marker + one-time cleanup DELETE, or new migration helper)
- `apps/api/web/app.py` (if cleanup is anchored at app construction instead of `connect`)
- `apps/api/tests/test_games_scrapers.py` (replace pinned assertions)
- `apps/api/tests/fixtures/` (add YasDL mixed-section fixture)
- `apps/web/src/app/page.tsx` (`handleCategoryChange`)

**Tests to add or update**
- Rewrite `test_downloadha_search_parsing`: assert invariant — every returned item's URL
  section is `game`, or `mobile` with `بازی` in title; assert the GTA OST item and GTasks are
  absent; keep the L.A Noire/ElAmigos assertions as over-filtering regression guards (ElAmigos
  is exactly the title the `ost` token would have broken). Prefer not to pin a bare count;
  if pinning, it is 8 on the current fixture.
- Add synthetic YasDL fixture (one game card, one non-game card in `post-title` markup) +
  test; assert only the game survives.
- Add cleanup-DELETE test: seed a mislabeled row + a correct row, run migration, assert the
  bad row (and its cascued variants/FTS entry) is gone, good row remains; re-run is a no-op
  (marker).
- e2e (Playwright, `e2e/specs/001-mvp/`, `e2e/fixtures/app.ts`): type query in Movies →
  switch to Games → assert input empty and no auto-search fired.

## Risks & Considerations

- **False-negative filtering**: a legitimate game filed outside `/game/` without the `بازی`
  marker is dropped. Mitigated by the `/mobile/`-marker carve-out; the music guard runs
  before the section check so a mis-filed OST under `/game/` is also caught.
- **Gate must NOT be marker-only anywhere**: the music post contains the game marker; any
  gate that trusts titles alone re-admits the exact reported symptom (measured: 9/10 kept).
- **Cleanup DELETE blast radius**: scoped by `source_id` + `category` + URL/title predicate;
  wrong predicate mass-deletes on fresh deploys if the marker is not persisted *before* the
  delete (make marker insert + delete one transaction). FTS and child tables stay consistent
  via existing trigger/cascades — do not bypass them.
- **Cache outlives DB cleanup**: in-memory TTL cache (`cache.py`, 45 min) may still serve
  pre-fix results after deploy; acceptable (self-heals) — call it out in the fix's test plan.
- **yasdl URL shapes unverified**: its section convention may differ from Downloadha's
  (`/game/` vs flat permalinks); inspect the site's real fixture/live behavior before
  copying the predicate. This is the one place evidence is thin.
- Test suite currently *documents* the wrong behavior (`len==10` + GTA assertion); whoever
  fixes this must update both deliberately, not flip them blindly.
- Stale `SPECIFY_FEATURE=006-music-sources-expansion` in the environment misdirects Spec Kit
  resolvers; unset it or create a real feature spec before `/speckit-plan`.

## Open Questions

None material. (All five gate/cleanup/verification decisions were user-confirmed in
`clarifications.md` 2026-09-30; the yasdl section-convention check is a task within the fix,
not a decision.)

---

Next: `/speckit-bug-fix slug=search-tab-bugs`
