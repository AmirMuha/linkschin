# Decision: Scraper Search Result Relevance & Noise Elimination

- **Slug**: search-result-relevance
- **Decided**: 2026-09-30
- **Verdict**: go
- **Artifacts reviewed**: intake.md | research.md | problem.md | concept.md

## Scorecard

| Criterion | Rating | Justification |
|-----------|--------|---------------|
| Problem validity | strong | Confirmed via user screenshot and reproducible on `uptvs_search.html` fixture. 100% of UpTVs queries append 3 static modal links. |
| Evidence strength | strong | Exact DOM lines identified (`uas_search_modal__categories__list__item` in lines 1306–1335 vs `content-thumb` in lines 392–735). |
| Value vs. inaction | strong | Completely eliminates irrelevant search noise, prevents cache/DB pollution, and fixes missing poster thumbnails. |
| Feasibility / appetite | strong | Clean, high-impact fix confined to `apps/api/sources/movies/uptvs.py` and test suite. Short diff, zero dependencies. |
| Strategic fit | strong | Restores search accuracy and visual polish across media aggregator. |
| Risk posture | low | Low risk of regression; covered by hermetic pytest fixtures. |

## Verdict & Rationale

**Verdict: GO.**
The root cause is fully verified. Fixing `parse_search_results` in `UpTVsPlugin` to parse within `content-thumb` blocks and ignore `uas_search_modal` links eliminates "Silo", "SpongeBob", and "From" entirely and provides instant poster artwork for movie search cards.

## Handoff Summary

- **Problem**: UpTVs scraper parses global anchor tags, capturing static search modal links ("سیلو", "باب اسفنجی", "From") on every query and omitting poster images.
- **Chosen approach**: Option 2 — Scope `UpTVsPlugin.parse_search_results` to `content-thumb` containers, extract poster URLs directly, explicitly filter modal navigation links, and assert absence of noise in tests.
- **In scope**:
  - `apps/api/sources/movies/uptvs.py`: Scope search result parsing to `content-thumb` card elements, extract `poster_url`, filter out `uas_search_modal` items.
  - `apps/api/tests/test_movies_scrapers.py`: Add test assertions verifying noise titles ("سیلو", "باب اسفنجی", "From") are excluded and posters are extracted.
- **Out of scope**:
  - Changes to other scrapers (already container-scoped).
  - External search engine algorithm modifications.
