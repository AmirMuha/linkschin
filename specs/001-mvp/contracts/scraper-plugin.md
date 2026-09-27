# Contract: Scraper Plugin Interface

- **Feature**: `001-mvp`
- **Component**: `sources.base`
- **Status**: Draft

This contract defines the standard interface and behavior required for all source scraper plugins across Movies, Games, and Music.

---

## Python Interface Protocol

Every scraper module MUST implement the `SourcePlugin` protocol.

```python
from typing import Protocol, List
import httpx
from models import Category, SearchQuery, MediaItem, SourceConfig

class SourcePlugin(Protocol):
    """Protocol that every category source plugin must implement."""

    config: SourceConfig

    async def search(
        self,
        query: SearchQuery,
        client: httpx.AsyncClient
    ) -> List[MediaItem]:
        """
        Search the upstream source portal for the query.
        Returns a list of MediaItem cards with summary metadata.
        Must NOT raise uncaught network exceptions (should log and return []).
        """
        ...

    async def extract_links(
        self,
        item: MediaItem,
        client: httpx.AsyncClient
    ) -> MediaItem:
        """
        Extract direct download links and streaming URLs for a specific media item.
        Populates item.movie_variants, item.game_releases, or item.music_downloads.
        Returns the enriched MediaItem.
        """
        ...
```

---

## Behavioral Guarantees & Contract Rules

1. **Isolation & Exception Containment**:
   - Scrapers MUST NOT raise uncaught network errors (`httpx.HTTPError`, `httpx.TimeoutException`, etc.) out of `search()` or `extract_links()`.
   - On network error or unparseable markup, scrapers MUST catch exceptions, record an error diagnostic on the response, and return an empty list or partial results.
2. **Timeout Conformance**:
   - Each plugin MUST honor the client's timeout budget (`SourceConfig.timeout_seconds`, default 7.0s).
3. **Redirect Tracking**:
   - Scrapers MUST permit `client.get(..., follow_redirects=True)` to dynamically follow domain migrations (e.g. `domain.com` → `domain1.com`).
   - If an upstream redirect resolves to a different domain, the scraper SHOULD update its in-memory active base URL for subsequent calls.
4. **Link Hygiene**:
   - Download links extracted MUST be direct URLs pointing to downloadable media files (e.g. `.mp4`, `.mkv`, `.rar`, `.zip`, `.mp3`) or direct CDN download endpoints.
   - Ad shorteners, pop-up triggers, or intermediate ad referral links (`adf.ly`, redirect hops) MUST be filtered out or resolved before returning.
5. **No State Mutation**:
   - Plugins MUST be stateless between requests, storing zero user or session data. All state passes via `SearchQuery` and `MediaItem`.
