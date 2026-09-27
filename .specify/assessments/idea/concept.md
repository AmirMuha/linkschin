# Concept: Iranian Media Fetcher (Movies, Games & Music)

- **Slug**: idea
- **Created**: 2026-09-27
- **Recommended option**: Option A — Pluggable Multi-Media Direct Link Aggregator

## Options

### Option A — Pluggable Multi-Media Direct Link Aggregator
- **Sketch**: A web application featuring explicit category tabs (`Movies`, `Games`, `Music`). A modular, pluggable scraper engine queries targeted Iranian websites per category:
  - *Movies*: Film2Media, AvaMovie, Zarfilm, MoboMovie. Formats categorized by resolution and dub/sub status; opportunistic in-browser streaming when CORS permits, direct download buttons otherwise.
  - *Games*: YasDL, Downloadha, Game2DL / PersianDL. Extracts structured split-RAR part lists with part sizes, archive passwords, and a "Copy all links" button.
  - *Music*: Nex1Music, Pop-Music, RadioJavan, UpMusic. Features an embedded HTML5 audio player for 128k/320k preview playback alongside direct download links.
  All scraping uses a lightweight HTTP client following HTTP 301/302 redirects with configurable base domain overrides. Metadata resolved via category-specific APIs (TMDB for movies, RAWG/IGDB for games, native site tags for music). On-demand scraping with 30–60 min cache TTL.
- **Appetite**: Medium (2–3 weeks)
- **Trade-offs**:
  - *Wins*: Solves media discovery and download friction across all 3 key media domains in one unified interface. Multi-part game handling and inline music playback provide immediate utility. Low server bandwidth overhead (no video relaying).
  - *Sacrifices*: Requires maintaining scraper plugins across 8+ source websites. Video streaming is opportunistic rather than guaranteed for all movie sources.
  - *Risks*: Scraper rot when source websites change HTML layouts or CDN endpoints.
- **Rabbit holes**: Implementing automated CAPTCHA solvers; attempting full video proxying for movies.

### Option B — Full Hybrid Aggregator with Server-Side Media Relay
- **Sketch**: Aggregates all three categories, but adds a server-side video proxy and caching layer to guarantee seamless in-browser video streaming for every movie and game preview.
- **Appetite**: Large (6–10 weeks)
- **Trade-offs**:
  - *Wins*: Complete in-browser video playback for all movie titles.
  - *Sacrifices*: Massive bandwidth and compute bills; high risk of hosting provider termination for relaying copyrighted video streams; high architectural complexity.
  - *Risks*: Bandwidth cost explosion, streaming buffering, severe legal exposure.
- **Rabbit holes**: HLS playlist rewriters, segment proxying, server CDN caching.

### Option C — Outbound Directory Search Index
- **Sketch**: Unified search portal that indexes release titles across movie, game, and music portals, providing outbound links to source post pages rather than deep-extracting media download links.
- **Appetite**: Small (1 week)
- **Trade-offs**:
  - *Wins*: Lowest maintenance; immune to download link format changes.
  - *Sacrifices*: Leaves users exposed to pop-unders, deceptive download buttons, and manual multi-part game copying on target sites.
  - *Risks*: Low user retention due to lack of direct link delivery.
- **Rabbit holes**: None, but minimal user value.

## Recommendation

**Option A (Pluggable Multi-Media Direct Link Aggregator)** is recommended.
It directly satisfies user demands across Movies, Games, and Music while keeping server resource consumption lightweight and sustainable. It avoids the bandwidth traps of Option B while delivering genuine utility (clean direct links, structured multi-part game downloads, and inline music playback) that Option C fails to provide.

## Out of Scope (for the recommended option)

- Server-side video stream proxying or transcode caching.
- Paid VIP account bypass or subscription sharing.
- Automated CAPTCHA solving farms.
- Native mobile or desktop applications (web application only).
- User accounts, favorites sync, or social commenting in MVP.

## Assumptions to Validate

- Initial Iranian target sites across Movies, Games, and Music maintain open public download links without mandatory VIP logins.
- Target music MP3 links permit cross-origin audio playback in HTML5 `<audio>` players.
- Game scrapers can consistently parse split archive part numbering and passwords from target HTML structures.
- Lightweight HTTP client can navigate initial anti-bot headers and follow domain redirect changes.
