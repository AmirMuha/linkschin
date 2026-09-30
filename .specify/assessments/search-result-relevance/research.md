# Research: Scraper Search Result Relevance & Noise Ingestion

- **Slug**: search-result-relevance
- **Created**: 2026-09-30
- **Inputs used**: user report, `Image #1`, `apps/api/sources/movies/uptvs.py`, `apps/api/tests/fixtures/uptvs_search.html`, `apps/api/web/app.py`

## Codebase Evidence & Verification

### 1. Root Cause in UpTVs Parser (`apps/api/sources/movies/uptvs.py`)
`UpTVsPlugin.parse_search_results` runs the following regex over the entire page HTML:
```python
pattern = re.compile(
    r'<a[^>]+href=[\"\'](https?://[^\"\'\s]+/contents/[^\"\']+)[\"\'][^>]*title=[\"\']([^\"\']+)[\"\']',
    re.IGNORECASE,
)
```
Inspection of `apps/api/tests/fixtures/uptvs_search.html` confirms:
- Lines 392–735: Real search results reside inside `<div class="content-thumb mb-20">` containers (15 items for query).
- Lines 1306–1335: The page includes a search modal (`<div class="uas_search_modal__categories">` with list `<div class="uas_search_modal__categories__list">` labeled "دسته‌های پیشنهادی" / Suggested categories).
- Hardcoded inside this modal:
  - `<a href="https://www.uptvs.com/contents/silo17.html" class="uas_search_modal__categories__list__item" title="سیلو">`
  - `<a href="https://www.uptvs.com/contents/spongebob-squarepants-animation-6.html" class="uas_search_modal__categories__list__item" title="باب اسفنجی">`
  - `<a href="https://www.uptvs.com/contents/from.html" class="uas_search_modal__categories__list__item" title="From">`
- Because the regex searches globally without container scoping or modal exclusion, items 16, 17, and 18 are unconditionally extracted as search results regardless of query.

### 2. Missing Poster Extraction in UpTVs Search
- Inside each `<div class="content-thumb mb-20">`, an `<img src="..." alt="...">` tag contains the movie poster.
- `UpTVsPlugin.parse_search_results` currently sets `poster_url=None`, only attempting extraction later in `extract_links` for the first 5 items (`found[:5]`).
- Consequently, cards in the search view render without posters ("بدون تصویر") as seen in the user's screenshot.

### 3. Comparison with Other Scraper Plugins
- `DoostihaaPlugin`: Scopes extraction to `<article>...</article>` tags. Sidebar and navigation links are not captured.
- `YasDLPlugin`: Scopes extraction to `<h[12] class="...post-title..."><a ...>`.
- `DownloadhaPlugin`: Scopes extraction to `<h[12] class="...entry-title..."><a ...>`.
- `PopMusicPlugin`: Scopes extraction to `<div class="music-card-pro">`.
- `Nex1MusicPlugin`: Scopes extraction to `<div class="post anm">`.
- `UpTVsPlugin` is the only scraper matching arbitrary anchor tags across the global document.

### 4. Aggregation Layer Gap (`apps/api/web/app.py`)
- `_collect_items` trusts plugin outputs blindly, doing `all_items.extend(res)`.
- There is no defensive token-based or fuzzy check ensuring that returned titles correlate with the user's search query (`SearchQuery.normalized_query` or `raw_query`).

## Impact

- 100% of searches hitting UpTVs include false-positive results ("سیلو", "باب اسفنجی", "From").
- High user confusion and degraded perceived search quality.
- Unnecessary database persistence and caching of irrelevant items.
