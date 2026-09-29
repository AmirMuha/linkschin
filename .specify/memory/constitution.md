# Iranian Multi-Media Direct Link Aggregator Constitution

## Core Principles

### I. Library / Module Isolation
Every scraper source is implemented as a standalone, decoupled plugin under `sources/` conforming strictly to the unified `SourcePlugin` protocol. No scraper may import or depend on sibling scraper implementations. Scrapers must handle their own parsing, domain normalization, and exception containment.

### II. Simplicity / YAGNI & Monorepo Platform Structure
The backend aggregator service (`apps/api`) favors lightweight, dependency-minimal endpoints exposing JSON metadata and direct links. The web interface (`apps/web`) operates as a Next.js application within the Turborepo monorepo, maintaining minimal dependencies (native HTML5 audio/video, utility-first Tailwind CSS, no redundant BFF or external state manager dependencies). No complex database servers or distributed message brokers. SQLite with FTS5 and in-memory TTL caching satisfy persistence and performance goals without external infrastructure baggage.

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

**Version**: 1.1.0 | **Ratified**: 2026-09-27 | **Last Amended**: 2026-09-29
