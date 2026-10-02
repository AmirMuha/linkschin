# Bug Assessment: source-links-redirect

- **Slug**: source-links-redirect
- **Created**: 2026-10-02T12:00:00Z
- **Source**: pasted text
- **Verdict**: valid
- **Severity**: medium

## Report (verbatim or summarized)

the following sources link doesn't work and won't redirect the user to the exact music page, sources: shenoto, farsichart, youtube_music, spotify, soundcloud, namasha,  please fix them.

## Symptom

When a user searches for music, the reference link provided for Shenoto, FarsiChart, YouTube Music, Spotify, SoundCloud, and Namasha does not correctly redirect them to the source's actual search results page. The default `/?s={term}` URL format is being used for all of them, which is incorrect for these specific platforms.

## Reproduction

1. Search for a track using one of the affected reference sources.
2. Click the provided `page_url` link in the result.
3. Observe that it goes to an invalid search path (e.g., `https://open.spotify.com/?s=term`) instead of the correct search page (e.g., `https://open.spotify.com/search/term`).

## Suspected Code Paths

- `apps/api/sources/music/reference.py` — The `search_url` method in `ReferenceSourcePlugin` defaults to `f"{self.base_url}/?s={quote_plus(term)}"`.
- `apps/api/sources/music/shenoto.py`
- `apps/api/sources/music/farsichart.py`
- `apps/api/sources/music/spotify.py`
- `apps/api/sources/music/youtube_music.py`
- `apps/api/sources/music/soundcloud.py`
- `apps/api/sources/music/namasha.py`
  — These plugin classes inherit `ReferenceSourcePlugin` but do not override the `search_url` method with their platform-specific search paths.

## Root Cause Hypothesis

High confidence. The `ReferenceSourcePlugin` provides a generic search URL (`/?s=query`) which doesn't match the actual search URL schemas for these third-party platforms. Since these plugins don't override the `search_url` method, they generate broken links.

## Proposed Remediation

**Preferred**: Override the `search_url(self, query: SearchQuery) -> str` method in each of the affected source plugin classes to return the correct platform-specific search URL.

For example:
- Spotify: `https://open.spotify.com/search/{term}`
- YouTube Music: `https://music.youtube.com/search?q={term}`
- SoundCloud: `https://soundcloud.com/search?q={term}`
- Namasha: `https://www.namasha.com/search?q={term}`

**Files likely to change**:
- `apps/api/sources/music/shenoto.py`
- `apps/api/sources/music/farsichart.py`
- `apps/api/sources/music/spotify.py`
- `apps/api/sources/music/youtube_music.py`
- `apps/api/sources/music/soundcloud.py`
- `apps/api/sources/music/namasha.py`

**Tests to add or update**:
- Add tests for each of these plugins to verify that `search_url` generates the correct URL format given a mock `SearchQuery`.

## Risks & Considerations

- Need to ensure we use the correct query parameter format for each site (e.g., URL encoding using `quote_plus`).

## Open Questions

- [NEEDS CLARIFICATION: Exact search URL structure for FarsiChart and Shenoto, as they might have specific paths like `/search?q=` or `/search/...]`]
