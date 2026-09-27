# Problem Definition: Iranian Media Fetcher (Movies, Games & Music)

- **Slug**: idea
- **Created**: 2026-09-27
- **Inputs used**: intake.md, research.md

## Problem Statement

Persian-speaking consumers looking for movies, PC/console games, and music suffer severe friction across fragmented Iranian download portals due to intrusive pop-under advertising, misleading download buttons, frequent domain churn, and tedious manual handling of split multi-part archives and format options.

## Affected Users & Stakeholders

- **Users**:
  - *Movie seekers*: Frustrated by ad redirect loops, expired links, and unorganized dub/sub formats.
  - *Gamers*: Forced to navigate ad walls and manually copy dozens of split RAR part links and passwords for 20–80GB game releases.
  - *Music listeners*: Overwhelmed by banner clutter when seeking clean 320kbps MP3 downloads or quick audio previews.
- **Stakeholders**:
  - *Product Owner (amirmuha)*: Desires a unified, pluggable media aggregator that simplifies discovery and extraction across all three media domains.
  - *Maintainers*: Require a modular plugin system so individual site DOM changes can be patched without breaking other categories.

## Goals

- Provide a single, clean search application with explicit category tabs (`Movies`, `Games`, `Music`).
- Extract direct download links categorized cleanly by media type:
  - Movies: resolution (480p, 720p, 1080p, x265) and language track (Persian dub vs subtitles).
  - Games: structured multi-part lists (Part 1..N), sizes, archive passwords, and one-click "Copy all links" action.
  - Music: quality options (128kbps, 320kbps) with integrated inline audio player and direct download links.
- Implement a pluggable scraper engine enabling new Iranian websites to be added easily.
- Support multilingual and localized search queries (Persian and English).

## Non-Goals

- Storing, caching, or hosting media files or game archives on application servers.
- Running a heavy server-side video streaming relay or transcode proxy.
- Bypassing paid VIP subscriptions or paywalls (public/free download links only).
- Automated CAPTCHA solving farms.
- Native mobile or desktop applications in MVP.

## Success Metrics

- **Search Latency**: Query results and extracted links displayed in < 5 seconds for cached queries, < 15 seconds for uncached multi-source queries.
- **Link Availability**: At least one valid download link returned for >80% of popular queries across all three categories.
- **Direct Link Integrity**: Over 90% of displayed links successfully initiate direct downloads without immediate HTTP 403/404 errors.
- **Multi-Part Integrity**: 100% of game archive parts and passwords correctly extracted and formatted.

## Cost of Inaction

Users continue spending significant time navigating predatory advertising, copying individual game parts manually, and hunting across dozens of bookmarks for active unblocked domains.

## Open Questions (All Resolved)

- **UI Navigation**: Explicit category tabs (`Movies`, `Games`, `Music`).
- **Target Site Plugins**: Pluggable architecture starting with:
  - Movies: Film2Media, AvaMovie, Zarfilm, MoboMovie.
  - Games: YasDL, Downloadha, Game2DL / PersianDL.
  - Music: Nex1Music, Pop-Music, RadioJavan, UpMusic.
- **Game Handling**: Structured part list with file sizes, passwords, and "Copy all links" button.
- **Audio Playback**: Inline HTML5 `<audio>` player for MP3 streams.
- **Movie Streaming**: Opportunistic browser streaming; direct download buttons fallback.
- **Metadata**: Category-specific APIs (TMDB, RAWG/IGDB, native).
- **Domain Shifts**: Automatic 301/302 redirect following + configuration overrides.
- **Caching**: On-demand real-time fetching with 30–60 minute TTL cache.
