# Quickstart: Validating Movie Source Expansion

- **Feature**: `005-movie-source-expansion`
- **Date**: 2026-09-30

Runnable checks that prove the feature works end-to-end. Every check here runs **offline** —
no upstream site is contacted (Constitution Principle IV).

For field semantics see [data-model.md](data-model.md); for request/response shapes see
[contracts/api-contract.md](contracts/api-contract.md).

---

## Prerequisites

```bash
cd apps/api
# Dependencies are already declared in pyproject.toml; no new packages are added by this feature.
uv sync            # or: pip install -e ".[dev]"
```

---

## Check 1 — All 20 requested sites are registered

Proves SC-001 and FR-001: no requested site is missing, including dead ones.

```bash
cd apps/api && python - <<'PY'
from sources import get_all_source_configs

REQUESTED = {
    "filimo","namava","filmnet","gapfilm","telewebion","aparat","imvbox","danfilo",
    "filmchiin","filmtarin","babakfilm","ndamedia","sarvnema","salamcinema","tiwall",
    "uptvs","namasha","rubika","digitoon","fam",
}
have = {c.id for c in get_all_source_configs()}
missing = REQUESTED - have
print("registered:", len(REQUESTED & have), "/ 20")
print("missing:", missing or "none")
assert not missing, f"unregistered requested sites: {missing}"
PY
```

**Expected**: `registered: 20 / 20`, `missing: none`.

> UpTV is pre-existing and must resolve to the existing entry, not a duplicate (FR-002).

---

## Check 2 — Fallback address is used when the primary is dead

Proves FR-012a and SC-009a: Filmnet's primary (`filmnet.film`) does not resolve, so the fallback
must serve the request.

```bash
cd apps/api && python - <<'PY'
from sources import get_all_source_configs
cfg = next(c for c in get_all_source_configs() if c.id == "filmnet")
print("addresses, in order:", cfg.base_urls)
print("primary:", cfg.primary_base_url)
assert len(cfg.base_urls) > 1, "no fallback address configured for filmnet"
PY
```

**Expected**: more than one address, primary first.

**Then, once implemented**, confirm the breaker skips a known-dead address rather than retrying it
on every request — see Check 5.

---

## Check 3 — Invalid profile address is rejected at load

Proves FR-014: a malformed address must be rejected, not silently dropped or requested.

```bash
cd apps/api && python - <<'PY'
import tempfile, pathlib
from sources.profiles import load_profiles

bad = pathlib.Path(tempfile.mkdtemp()) / "p.yaml"
bad.write_text(
    "sources:\n"
    "  - id: testsite\n    name: Test\n    category: movies\n"
    "    provides_downloads: true\n    parser: html_wordpress_list\n"
    "    addresses:\n      - not-a-url\n"
)
try:
    load_profiles(bad)
    print("FAIL: invalid address was accepted")
except Exception as e:
    print("rejected as expected:", type(e).__name__, e)
PY
```

**Expected**: a validation error naming the source id and the offending value.

---

## Check 4 — Offline parser test for a new source

Proves FR-025 and SC-010: a new source is verifiable with no network.

```bash
cd apps/api && python -m pytest tests/test_movies_scrapers.py -q
```

**Expected**: all tests pass with no network access. A new source contributes one search-fixture
test and one item-fixture test, following the existing `uptvs` / `doostihaa` convention.

---

## Check 5 — A failing source does not break the search

Proves FR-010 and SC-004: with sources failing, the rest still return results.

```bash
cd apps/api && python -m pytest tests/test_sources_config.py -q
```

**Expected**: a test in which every address for one source errors, and the search still returns
items from the healthy sources within the 10s budget.

---

## Check 6 — No download link is produced for a subscription source

Proves FR-006, FR-007 and SC-007 — the constitutional boundary. This is the most important check
in the document.

```bash
cd apps/api && python -m pytest tests/test_movies_scrapers.py -q -k "watch_only or subscription"
```

**Expected**: for every source whose `provides_downloads` is `False`, any returned item has
`watch_url` set and `movie_variants` **empty**. A failure here is a blocking defect, not a bug to
work around.

---

## Check 7 — Silent markup break is detected

Proves FR-019 and SC-011: HTTP 200 with nothing parseable must not read as "no matching titles".

```bash
cd apps/api && python -m pytest tests/test_sources_config.py -q -k "silent or consecutive"
```

**Expected**: a source returning a valid but unparseable page increments `consecutive_failures` and
is eventually reported as degraded in `/api/health`.

---

## Check 8 — End-to-end against the local server

```bash
# Terminal 1
cd apps/api && pnpm --filter @repo/api dev     # or: python -m uvicorn main:app --port 8000

# Terminal 2 — all 20 sites present, with state and reason
curl -s localhost:8000/api/sources | python -m json.tool | head -40

# A known subscription title returns a watch_url and no variants
curl -s "localhost:8000/api/search?q=Inception&category=movies&refresh=true" \
  | python -c "import json,sys; d=json.load(sys.stdin); [print(i['source_id'], '| watch:', i.get('watch_url'), '| variants:', len(i['movie_variants'])) for i in d['items']]"

# Health shows per-source state including a source with consecutive failures
curl -s localhost:8000/api/health | python -c "import json,sys; print(json.load(sys.stdin)['source_health_counts'])"
```

**Expected**:
- `/api/sources` lists **20** entries, each with `state` and, when inactive, `inactive_reason`.
- No item for a gated title has a non-empty `movie_variants`.
- `/api/health` returns `source_health_counts` summing to the number of registered sources.

---

## Check 9 — No media payload is relayed

Proves FR-026 and SC-008.

```bash
cd apps/api && python -m pytest tests/test_streaming.py -q
```

**Expected**: passes. The server returns metadata and upstream URLs only; it never streams bytes.
`watch_url` points at the source's own page and is not fetched or proxied by the server.

---

## Check 10 — Pre-existing sources are unaffected

Proves FR-024 and SC-012: the sources that work today must not regress.

```bash
cd apps/api && python -m pytest tests/ -q
```

**Expected**: the full existing suite passes unchanged, including the current `uptvs`,
`doostihaa`, `downloadha`, `yasdl`, `popmusic`, and `nex1music` tests.

---

## Full validation

```bash
cd apps/api && python tests/run_all.py     # offline runner, per pyproject "test-offline" task
```

---

## Known limitation

Four sites have **no confirmed working address** and are shipped as a recorded gap, not as a
passing check. They register, load, and report health state like any other source, but there is no
captured HTML, so no parser fixture and no `parse_search_results` test exists for them. Every other
movie source added by 005 is covered by `tests/test_movie_sources.py`.

| id | Site | Why no address is confirmed | Health state seeded |
|----|------|------------------------------|--------------------|
| `ndamedia` | Nda Media | No verified domain | `not_yet_proven` |
| `salamcinema` | Salam Cinema | No verified domain | `not_yet_proven` |
| `tiwall` | Tiwall | Permanent redirect loop (307) | `not_yet_proven` |
| `fam` | Fam | Permanent redirect loop (308) | `not_yet_proven` |

The four ids and their reasons live in `apps/api/sources/health.py::INITIAL_UNPROVEN_SITES`, so
`/api/health` reports them as `not_yet_proven` with a reason rather than silently reporting
`providing_results` for a source that has never answered.

**To close the gap**: supply a working address, capture a search page to
`apps/api/tests/fixtures/<id>_search.html`, and add the matching case to `PARSER_BY_SOURCE` in
`tests/test_movie_sources.py`. The parsers exist and are registered; only the captured markup is
missing. Note that the address list, not a hardcoded host, is what a parser reads — an address
change is configuration alone.

Bounded-redirect handling (T079, FR-015) is what keeps `tiwall` and `fam` from hanging the search:
their loops now surface as a `RedirectLoopError` after `MAX_REDIRECTS` hops instead of spinning.
See research.md R-001 and R-008.
