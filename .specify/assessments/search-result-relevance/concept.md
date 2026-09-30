# Concept: Container-Scoped Scraping & Defensive Relevance Gating

- **Slug**: search-result-relevance
- **Created**: 2026-09-30
- **Inputs used**: problem.md, research.md

## Solution Options

### Option 1: Scoped Container & Poster Parsing in UpTVs (Targeted Fix)
- Modify `UpTVsPlugin.parse_search_results` in `apps/api/sources/movies/uptvs.py`:
  - Split search HTML or match `<div class="content-thumb mb-20">(.*?)</div>\s*</div>` (matching other plugins like `popmusic` and `yasdl`).
  - Extract the primary post anchor inside each `content-thumb`.
  - Extract the poster thumbnail URL from `<img src="...">` inside the `content-thumb` block.
  - Reject any links found inside `div.uas_search_modal` or containing class `uas_search_modal__categories__list__item`.
- **Pros**: Direct root-cause fix, minimal code diff (YAGNI/Ponytail), zero changes to other sources.
- **Cons**: Does not guard against other scrapers that might leak noisy results if upstream changes.
- **Appetite**: Small (1–2 hours).

### Option 2: Container Scoping + Generic Scraper Noise Exclusion (Recommended)
- Implement Option 1 in `UpTVsPlugin` (scope to `content-thumb` and capture `poster_url`).
- Also ensure that if UpTVs markup changes slightly, anchors with class `uas_search_modal__categories__list__item` or parent `uas_search_modal` are explicitly filtered out.
- Update `test_movies_scrapers.py` to assert that:
  - Exact count of results matches expected real items (15).
  - "سیلو", "باب اسفنجی", and "From" are explicitly absent.
  - `first.poster_url` is populated and valid.
- **Pros**: Eliminates bug completely, prevents recurrence, fixes missing posters on UI cards, leaves clean tests.
- **Cons**: None.
- **Appetite**: Small (half day).

## Trade-offs & Recommendation

**Recommendation**: Option 2.
Directly adheres to Ponytail principles: fix root cause where the leak happens (`uptvs.py`), extract poster where it already exists natively in HTML, and verify with unit tests.
