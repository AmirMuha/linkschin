# Quickstart: Validating Music Source Expansion

**Feature**: [006-music-sources-expansion](./spec.md) | **Date**: 2026-09-30

A runnable guide to verify the feature end to end. Each scenario maps to a numbered requirement or success criterion so gaps are traceable.

## Prerequisites

| Requirement | Check |
|---|---|
| Python 3.11+ | `python3 --version` |
| Project virtualenv | `.venv` present at repo root |
| Network access to the target portals | Only needed for the optional live-capture step below. **Every automated check runs without it.** |

```bash
cd /run/media/amirmuha/0C944DAF23695833/projects/movie-fetcher/apps/api
```

## 1. Automated checks (no network)

This is the gate. SC-004 requires 100% of new sources to pass with the network unavailable.

```bash
poe test-offline
```

Expected: the full suite passes with no network access. Specifically:

| Test file | Asserts |
|---|---|
| `tests/test_reference_sources.py` | All 9 reference plugins yield `stream_url is None` and `music_tracks == []` |
| `tests/test_source_kind.py` | Ordering, the 3-failure threshold and its reset, registry shape |
| `tests/test_music_scrapers.py` | One parser test per full source against a committed fixture |
| `tests/test_sources_config.py` | All 20 named sites present, each with an explicit kind |
| `tests/test_movies_scrapers.py`, `tests/test_games_scrapers.py` | **Unchanged** — proves FR-028 (no regression) |

To prove the offline claim rather than assume it:

```bash
poe test-offline && echo "PASSED WITHOUT NETWORK"
```

**ponytail: if a source has no captured fixture yet, skip it rather than blocking the suite.** Record the source in the registry with its real status and a reason, and add the test when a capture exists. FR-019 requires every source to be *verifiable*, not that verification happen before the source ships.

## 2. Lint and type checks

```bash
poe lint                      # backend compile check
cd ../../apps/web && pnpm check   # tsc --noEmit
```

Expected: both clean.

## 3. Source registry (FR-017, SC-007)

```bash
poe start &
curl -s localhost:8000/api/sources | python3 -m json.tool | head -60
```

Verify by inspection:

1. All 20 named sites appear — Radio Javan, Musicdel, Nex1Music, Music-fa, UpSong, UpMusics, MusicTarin, Tehran Music, Shenoto, Melodify, TakMusics, 1RJ, FarsiChart, Aparat, Namasha, Rubika, Fam, SoundCloud, Spotify, YouTube Music.
2. Every entry has `kind` (`full` or `reference`).
3. 11 entries are `full`, 9 are `reference`.
4. Every entry whose `status` is not `active` has a **specific** `inactive_reason` — a changed domain, a dead domain, an account requirement, a licensed service, a video platform, or gated access. A generic "error" fails this check.
5. `nex1music` and `radiojavan` appear **once each**, not duplicated (FR-024).

## 4. Search returns both kinds (FR-002, SC-001)

```bash
curl -s "localhost:8000/api/search?q=%D9%85%D8%AD%D8%B3%D9%86&category=music" \
  | python3 -c "
import json,sys
d=json.load(sys.stdin)
items=d['items']
kinds={}
for i in items: kinds.setdefault(i.get('source_kind','full'),0); kinds[i['source_kind']]+=1
print('kind counts:', kinds)
print('total items:', len(items))
print('distinct sources:', len({i['source_id'] for i in items}))
"
```

Expected: at least 6 distinct sources, and both `full` and `reference` kinds present when a reference source has a match for the term.

**A Persian term is used above deliberately.** FR-006 requires NFKC normalization plus Arabic/Persian character and digit variants, so a query in the wrong script should still return results:

```bash
# Arabic yeh (ي) and Arabic-Indic digits (٣) instead of Persian yeh (ی) and ASCII digits
curl -s "localhost:8000/api/search?q=%D9%85%D8%AD%D8%B3%D9%86%20%D9%8A%D9%83%203&category=music" | head -c 300
```

Expected: comparable results, not an empty set.

## 5. Ordering: full before reference (FR-005a)

```bash
curl -s "localhost:8000/api/search?q=test&category=music" | python3 -c "
import json,sys
kinds=[i.get('source_kind','full') for i in json.load(sys.stdin)['items']]
order={'full':0,'reference':1}
ranks=[order.get(k,0) for k in kinds]
print('kinds:', kinds)
print('ORDERING OK' if ranks==sorted(ranks) else 'ORDERING VIOLATED')
"
```

Expected: `ORDERING OK`. This is the direct check for the clarify-session decision.

## 6. Reference results carry no media (FR-011, FR-012, SC-008)

```bash
curl -s "localhost:8000/api/search?q=test&category=music" | python3 -c "
import json,sys
bad=[]
for i in json.load(sys.stdin)['items']:
    if i.get('source_kind')=='reference':
        if i.get('stream_url') or i.get('music_tracks'): bad.append(i['id'])
print('LEAKED MEDIA:', bad) if bad else print('CLEAN — no reference item carries media')
"
```

Expected: `CLEAN`. Any id listed here is a Principle III violation.

## 7. Per-user hide filter (FR-029, FR-030, FR-031)

```bash
# With one source hidden
curl -s "localhost:8000/api/search?q=test&category=music&sources=aparat" \
  | python3 -c "import json,sys; print(sorted({i['source_id'] for i in json.load(sys.stdin)['items']}))"

# Without the filter
curl -s "localhost:8000/api/search?q=test&category=music" \
  | python3 -c "import json,sys; print(sorted({i['source_id'] for i in json.load(sys.stdin)['items']}))"
```

Expected: the first response contains no `aparat` items; the second does. A difference confirms the filter applies to that request only.

An unknown id must be ignored rather than rejected:

```bash
curl -s -o /dev/null -w "%{http_code}\n" "localhost:8000/api/search?q=test&category=music&sources=does-not-exist"
```

Expected: `200`.

## 8. Degraded threshold (FR-018a, SC-009)

The threshold is 3 *separate searches*, and any success resets it.

```bash
for i in 1 2 3; do
  curl -s -o /dev/null "localhost:8000/api/search?q=zzz-nonexistent&category=music&refresh=true"
  curl -s localhost:8000/api/sources | python3 -c "
import json,sys
s=[x for x in json.load(sys.stdin) if x['id']=='musicdel'][0]
print(f\"after search $i: status={s['status']} failures={s['consecutive_failures']}\")
"
done
```

Expected progression: `active` at 1 and 2 failures, then `degraded` at 3. A source at 1–2 failures MUST still show `active` — that is what prevents a momentary outage from flickering a healthy source off the list.

Then confirm a success resets it:

```bash
curl -s "localhost:8000/api/search?q=<a-real-track>&category=music&refresh=true" > /dev/null
curl -s localhost:8000/api/sources | python3 -c "
import json,sys
s=[x for x in json.load(sys.stdin) if x['id']=='musicdel'][0]
print('after success:', s['status'], s['consecutive_failures'])
"
```

Expected: `active` with `0`.

## 9. Partial-failure resilience (FR-007, SC-005)

Disable one source and confirm others still return:

```bash
MOVIE_FETCHER_ENABLE_MUSICDEL=0 poe start &
curl -s "localhost:8000/api/search?q=test&category=music" \
  | python3 -c "import json,sys; print('sources returned:', sorted({i['source_id'] for i in json.load(sys.stdin)['items']}))"
```

Expected: results from remaining sources, plus a `warnings` entry naming the failed one. No error response.

## 10. No regression in other categories (FR-028, SC-010)

```bash
curl -s "localhost:8000/api/search?q=dilan&category=movies" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('movies items:', len(d['items']))"
curl -s "localhost:8000/api/search?q=gta&category=games" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('games items:', len(d['items']))"
```

Expected: both return results in the existing shape, every item with `source_kind` present. The offline test suite in step 1 is the stronger check, since it compares against the pre-existing expectations.

## 11. Browser check (SC-002, SC-003)

```bash
cd ../../apps/web && pnpm dev
```

Open the app, search a Persian track under the music category, and confirm:

1. Playable results appear above link-out results.
2. A full-source result shows a working player and download controls.
3. A reference result shows **no** player and **no** download button — verify in devtools that no `<audio>` element exists in the DOM, not merely that it is invisible.
4. Activating a reference result opens the correct page on the originating site in a new tab.
5. The source list shows a kind badge and, for any inactive source, a specific reason.
6. Hiding a source removes its results and survives a page reload; the source remains listed so it can be restored.
7. Network inspector shows every media request going **directly to the upstream host**, with none passing through `localhost:8000` (FR-013, SC-008).

Step 7 is the definitive check for Principle III. If any media request hits the aggregator, the feature has failed its non-negotiable constraint regardless of what the tests say.

## 12. Optional: capturing a source fixture

Only needed for a source not yet captured. Requires network access to the portal.

```bash
# 1. Resolve the source's search URL
poe check --category music --source <source_id> --query "<term>"

# 2. Save the raw response as the fixture
curl -s "<search-url>" -o tests/fixtures/<source_id>_search.html

# 3. Repeat for a track detail page
curl -s "<track-page-url>" -o tests/fixtures/<source_id>_item.html

# 4. Add fixtures to conftest.py following the existing pattern, then write the parser test
poe test-offline
```

**ponytail: trim fixtures to a representative slice.** A full search page can be megabytes of markup; keeping a few complete result cards is enough to exercise the parser and keeps the repo light. Trim after verifying the tests still pass — a trimmed fixture that silently stops covering a selector is worse than a large one.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `sources` parameter ignored | Filter applied after plugin selection instead of before, or applied before the cache check |
| Filtered results leak to another user | The filtered set was written to `GLOBAL_CACHE` — the cache must only ever hold the unfiltered set |
| Reference item shows a player | Template renders the player unconditionally, or relies on CSS hiding |
| `consecutive_failures` column missing | The `ALTER TABLE` guard did not run; `CREATE TABLE IF NOT EXISTS` does not add columns to an existing table |
| A source never reaches `degraded` | Counter incremented per request rather than per completed search |
| Ordering looks random | Sort applied before the gather, or an unstable sort key varying within a kind |
