# Idea Research: User Source Suggestion Form

- **Slug**: source-suggestions
- **Created**: 2026-09-29
- **Evidence confidence (overall)**: high

## Users & Demand

- **Scraper coverage gaps**: Users frequently discover and use Persian media hubs, blogs, or forums that the application does not yet index — [source: codebase inspection of existing scrapers in `apps/api/sources/` (uptvs, doostihaa, yasdl, nex1music)] (confidence: high)
- **Friction in reporting**: Without an in-app form, reporting new sources requires opening a GitHub issue or contacting maintainers directly, which non-technical users avoid — [ASSUMPTION based on developer-centric GitHub workflow] (confidence: medium)
- **Demand for missing media types / niches**: Niche media categories (e.g., specialized foreign series, lossless audio, retro games) often live on dedicated sites best identified by active consumers — [ASSUMPTION] (confidence: high)

## Prior Art

- **Existing Sources Architecture**: `apps/api/sources/` has pluggable `BaseSource` scrapers (`movies/`, `games/`, `music/`). Each scraper requires custom DOM parsing and URL resolution — [source: `apps/api/sources/base.py`]
- **Source Status Bar in UI**: `apps/web/src/components/SourceStatusBar.tsx` displays active sources and status to users; providing a natural entry point (e.g., "Suggest a Source" button) — [source: `apps/web/src/components/SourceStatusBar.tsx`]
- **Community Indexer Requests**: Open-source aggregators (Jackett, Prowlarr, Stremio) rely heavily on standardized source request templates to gather site details, sample URLs, and authentication constraints — [source: external open-source conventions]

## Market & Context

- **Domain churn**: Iranian media hosting sites frequently change TLDs or domains due to ISP filtering or hosting migrations. Community submissions provide early warning and new candidate domains — [ASSUMPTION based on regional web ecosystem] (confidence: high)
- **Cost of doing nothing**: Scraper additions remain bottlenecked on maintainer browsing habits, leaving high-traffic media sources unindexed.

## Data & Constraints

- **Submission Volume**: Low to moderate (< 100 submissions per month for typical self-hosted or small-community deployments) — [ASSUMPTION] (confidence: high)
- **Storage**: Project uses zero-dependency stdlib `sqlite3` (`apps/api/db.py`). A lightweight table (`source_suggestions`) integrates seamlessly with no new infrastructure — [source: `apps/api/db.py`]
- **Rate Limiting**: Sliding window IP tracker in FastAPI middleware or simple SQLite query `COUNT(*) WHERE ip = ? AND created_at > ?` prevents spam without requiring Redis — [source: project minimal-dependency architecture]
- **Validation**: Source URLs must be validated for valid scheme (`http`/`https`), normalized domain, and reasonable length limits to prevent DB pollution.

## Evidence Against the Idea

- **Scraper development bottleneck**: Collecting suggestions does not automate scraper creation. Each source still requires human reverse-engineering of markup, download links, and pagination. A backlog of unfulfilled suggestions may frustrate users — [source: maintenance complexity of web scrapers]
- **Spam & invalid URLs**: Open submission forms attract SEO spam, affiliate links, dead sites, or paywalled services — [ASSUMPTION]
- **Proxy header trust**: IP rate limiting relies on `request.client.host` or `X-Forwarded-For`. Without trusted proxy configuration, malicious actors could cycle fake header IPs.

## Gaps & Open Questions

- **De-duplication**: Resolved — duplicate domain/URL submissions increment request counter rather than erroring or polluting the database.
- **Admin Triage**: Resolved — `GET /api/admin/suggestions` protected endpoint for maintainer review.
- **User Feedback**: Resolved — success toast notification; fire-and-forget.
- **Rate Limit**: Resolved — 10 submissions per day per client IP.

## Sources

- `apps/api/sources/base.py` (host: local repo)
- `apps/api/db.py` (host: local repo)
- `apps/web/src/components/SourceStatusBar.tsx` (host: local repo)
