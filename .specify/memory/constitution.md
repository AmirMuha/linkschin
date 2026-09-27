# Iranian Multi-Media Direct Link Aggregator Constitution

## Core Principles

### I. Library / Module Isolation
Every scraper source is implemented as a standalone, decoupled plugin under `sources/` conforming strictly to the unified `SourcePlugin` protocol. No scraper may import or depend on sibling scraper implementations. Scrapers must handle their own parsing, domain normalization, and exception containment.

### II. Simplicity / YAGNI
The application favors server-rendered HTML using Jinja2 and vanilla modern CSS. No Node/npm SPA build pipelines, no complex database servers, and no distributed message brokers. In-memory caching with TTL satisfies performance goals without infrastructure baggage.

### III. No Media Relaying (NON-NEGOTIABLE)
The application server acts solely as a metadata aggregator and direct link extractor. Under no circumstances may the server buffer, proxy, download, or relay video, audio, or game archive payloads through its own network interface. All media streaming and downloading routes directly from the user's client to upstream CDNs.

### IV. Testability & Offline Verification
Every scraper plugin must be verifiable offline using static HTML fixtures with mocked HTTP clients (`respx`). Network instability or upstream domain churn must never block automated test suites.

## Quality Gates & Constraints

- All search queries undergo Persian/Arabic Unicode normalization (NFKC).
- Split game archives must maintain strict sequential ordering; gaps must be flagged, not silently ignored.
- Upstream HTTP timeouts are strictly budgeted (7s per source, 10s per search request).

## Governance

This constitution governs all feature planning, implementation, and code review. Changes to principles require explicit amendment and justification.

**Version**: 1.0.0 | **Ratified**: 2026-09-27 | **Last Amended**: 2026-09-27
