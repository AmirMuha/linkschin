# Bug Fix: source-links-redirect

- **Slug**: source-links-redirect
- **Fixed**: 2026-10-02T12:00:00Z
- **Assessment**: ./assessment.md
- **Status**: applied

## Summary

Overrode the `search_url` method in the Shenoto, FarsiChart, YouTube Music, Spotify, SoundCloud, and Namasha plugins to point to their platform-specific search routes.

## Changes

| File | Change | Notes |
|------|--------|-------|
| `apps/api/sources/music/spotify.py` | modified | Used `/search/` path |
| `apps/api/sources/music/youtube_music.py` | modified | Used `/search?q=` |
| `apps/api/sources/music/soundcloud.py` | modified | Used `/search?q=` |
| `apps/api/sources/music/namasha.py` | modified | Used `/search?q=` |
| `apps/api/sources/music/shenoto.py` | modified | Used `/search?q=` |
| `apps/api/sources/music/farsichart.py` | modified | Used `/?q=` (generic client-side param) |
| `apps/api/tests/test_reference_search_urls.py` | added test | Verifies proper url formats |

## Diff Highlights (optional)

```python
    def search_url(self, query: SearchQuery) -> str:
        """Override default search URL."""
        term = query.normalized_query or query.raw_query
        return f"{self.base_url}/search/{quote_plus(term)}"
```

## Tests Added or Updated

- `apps/api/tests/test_reference_search_urls.py::test_custom_search_urls` — Verifies each plugin's `search_url` correctly formats its respective domain and search path.

## Local Verification

- Commands run: `uv run --with pytest pytest tests/test_reference_search_urls.py` → Passed
- Commands run: `uv run --with pytest pytest tests/test_reference_sources.py` → Passed

## Deviations from Assessment

For FarsiChart and Shenoto, as they lacked discoverable fixed endpoints for their SPAs when checked, standard parameterized structures (`/?q=` and `/search?q=`) were applied to avoid breaking completely. They may still require manual verification.

## Follow-ups

- Manually verify the search route functionality for Shenoto and FarsiChart once able to access them from a browser.
