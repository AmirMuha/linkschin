# Bug Verification: Games results include music posts; search term persists across tabs

- **Slug**: search-tab-bugs
- **Tested**: 2026-09-30
- **Assessment**: ./assessment.md
- **Fix**: ./fix.md
- **Result**: verified

## Summary

Both reported symptoms no longer reproduce, verified against the assessment's own
reproduction steps and at the API layer a user actually hits. One defect was found *in the
fix itself* during this pass — `_collect_items` filtered before persisting, which made the
"music tab can serve the soundtrack" claim in `fix.md` false — and it was corrected and
pinned with a regression test. Final state: 75 API tests and 5 e2e specs pass.

## Checks Performed

| Check | Command / Action | Result | Notes |
|-------|------------------|--------|-------|
| Reproduction (Bug 1, post-fix) | Parser over `tests/fixtures/downloadha_search.html` | pass | 9 cards, 0 offenders stamped `games` (was: 10 cards, GTA OST + GTasks stamped `games`) |
| Reproduction (Bug 1, at the API) | `/api/search?category=games&refresh=true` with the real plugin's real fixture output | pass | 8 items, 0 non-games leaked; verified via `TestClient`, not by inspection |
| Reproduction (Bug 1, DB cleanup) | Read-only query against the real `data/index.db` | pass | Marker `drop_misfiled_game_rows_v1` set, 0 misfiled rows remain, YasDL's 14 rows intact |
| Reproduction (Bug 2, post-fix) | `search-tab-bugs.spec.ts` | pass | Input empty after tab switch, no `/api/search` issued |
| New / updated tests | `pytest tests/ -q` | pass | 75 passed |
| New test is a real guard | Reverted the persist-then-filter ordering | pass | New test failed on the persistence assertion; restored and re-confirmed green |
| Regression suite (e2e) | `npx playwright test --project=hermetic-chromium` | pass | 5 passed (1 bug spec + 4 pre-existing movie specs) |
| App boots | `uvicorn main:app` on an isolated port, `/health` | pass | Startup clean, `database_stats` coherent |
| Lint / type-check | `npx tsc --noEmit` in `apps/web` | pass (with pre-existing failure) | One error in `src/lib/archive.test.ts`, untouched by this fix |

## Output Excerpts

Bug 1, the assessment's reproduction, re-run verbatim against the fixture:

```
cards returned: 9
BUG1 offenders in games tab: 0

[music] https://www.downloadha.com/others/gta-online-arena-war-ost/
[games] https://www.downloadha.com/game/ragtag-adventurers/
... (8 games total, all under /game/)
```

The same query at the API layer, which is what a user hits:

```
BUG1  games-response items: 8 | non-games leaked: 0 | offenders present: 0
BUG1  soundtrack persisted: 1 item(s) -> music tab can serve it
```

Migration against the developer's real index (read-only connection):

```
marker present: True
misfiled downloadha games rows: 0
yasdl rows intact: 14
```

Defect found and fixed during this pass — with the bad ordering, the new test fails exactly
on persistence:

```
>       assert [i.title for i in indexed] == ["دانلود موسیقی متن بازی Elden Ring"]
E       AssertionError: assert [] == ['دانلود موسیقی...ی Elden Ring']
```

Final runs:

```
75 passed, 1 warning in 0.45s
  5 passed (9.8s)
```

## Residual Risks

- **The live sites were never contacted.** Every check ran against the recorded fixtures and
  the hermetic stub. `is_game_post` is validated against Downloadha's *current* URL
  convention as captured on 2026-09-27. If that site reorganises its sections, real games
  would be dropped without any test failing. A live smoke test would close this.
- **The `/mobile/` carve-out is unvalidated against live markup.** The fixture has no
  `/mobile/` game post, so `test_downloadha_keeps_android_games_filed_under_mobile` proves
  the logic but not that real Android game posts are filed that way. The assessment flagged
  YasDL's section convention as its thin-evidence area; `/mobile/` is now the same.
- **The in-memory cache can still serve pre-fix results for up to 45 minutes** after a
  deploy. Self-healing, and explicitly accepted in the assessment.
- **`classify_post` is title-substring matching, so it is inherently approximate.** The
  `شبیه ساز` → Euro Truck Simulator collision was found and fixed; another Persian compound
  could collide the same way. A dropped real game is a silent failure mode.
- **e2e covers one browser project.** `hermetic-firefox` and `mobile-375` were not run
  (cost); the tab-switch logic is React state and carries no browser-specific risk.
- `src/lib/archive.test.ts` has a pre-existing `tsc` error unrelated to this fix.

## Recommendation

Close the bug — verified end-to-end against the assessment's reproduction, at both the
parser and the API layer, with a real-guard check on the new regression test. Before
deploying broadly, run one live smoke search on Downloadha in the games tab to confirm the
`/game/` and `/mobile/` URL conventions still hold against the real site; that is the one
assumption the fixture data cannot confirm, and a mismatch would silently drop real games
rather than raise an error.
