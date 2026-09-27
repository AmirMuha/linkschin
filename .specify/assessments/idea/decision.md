# Decision: Iranian Media Fetcher (Movies, Games & Music)

- **Slug**: idea
- **Decided**: 2026-09-27
- **Verdict**: go
- **Artifacts reviewed**: intake.md, research.md, problem.md, concept.md

## Scorecard

| Criterion | Rating | Justification |
|-----------|--------|---------------|
| Problem validity | strong | Ad spam, deceptive buttons, domain churn, and tedious multi-part links create acute friction across Iranian movie, game, and music portals. |
| Evidence strength | adequate | Technical characteristics of Iranian media portals (direct MP3s, split RAR game archives, movie dub/sub tiers, redirect shifts) are concrete and validated. |
| Value vs. inaction | strong | Unified search with clean direct downloads, organized multi-part game links, and inline audio playback solves an everyday user problem. |
| Feasibility / appetite | adequate | Option A fits a 2–3 week appetite with modular scraper plugins and no expensive video proxy bandwidth overhead. |
| Strategic fit | strong | Fully aligned with user requirements for an Iranian media aggregator spanning movies, games, and music. |
| Risk posture | adequate | Video proxying is avoided (opportunistic streaming only); media hosting liability is avoided (direct link extraction only); scrapers are isolated into plugins. |

## Verdict & Rationale

**Verdict: GO.**
The expanded problem definition (Movies, Games, Music) is clear and well-shaped. All initial ambiguities have been resolved through user input: explicit category tabs, pluggable scraper plugins, structured multi-part game archive handling with passwords, inline HTML5 audio streaming, and opportunistic movie streaming without a media proxy. Option A provides high value while strictly limiting operational and legal risks.

## If go — Handoff to `/speckit-specify`

- **Problem**: Persian-speaking internet users face extreme friction finding clean media links across fragmented Iranian websites due to invasive pop-under ads, broken domains, confusing multi-part game downloads, and scattered format options.
- **Chosen approach**: Option A — Pluggable Multi-Media Direct Link Aggregator. A fast web application with explicit category tabs (`Movies`, `Games`, `Music`), a modular scraper plugin engine for targeted Iranian portals, category-specific metadata resolution, structured split-archive presentation for games, and inline audio playback for music.
- **In scope**:
  - Web interface with category tabs (`Movies`, `Games`, `Music`) and search input.
  - Pluggable scraper architecture:
    - *Movies*: Film2Media, AvaMovie, Zarfilm, MoboMovie.
    - *Games*: YasDL, Downloadha, Game2DL / PersianDL.
    - *Music*: Nex1Music, Pop-Music, RadioJavan, UpMusic.
  - Movie direct download links categorized by resolution (480p, 720p, 1080p, x265) and audio track (Persian dub vs sub).
  - Opportunistic movie streaming where browser playback is unblocked (direct download buttons fallback).
  - Structured multi-part game archive links (Part 1..N), file sizes, archive extraction passwords, and "Copy all links" action.
  - Music 128k/320k direct download links with integrated inline HTML5 `<audio>` player.
  - Category-specific metadata enrichment (TMDB for movies, RAWG/IGDB for games, native site metadata for music).
  - Lightweight HTTP scraper client with custom headers, cookie handling, automatic 301/302 redirect tracking, and configurable base domain overrides.
  - On-demand fetching with short TTL in-memory caching (30–60 min).
- **Out of scope**:
  - Server-side media proxying, relaying, or transcode caching.
  - Paid VIP account bypass or subscription sharing.
  - Automated CAPTCHA solving farms.
  - Native mobile or desktop applications.
- **Success metrics**:
  - Search-to-link latency < 5s cached, < 15s live multi-source query.
  - >80% link extraction availability across top queries in all three categories.
  - >90% direct download link validity.
  - 100% of game archive parts and passwords correctly parsed.
- **Carried-forward open questions (Resolved)**:
  - All category scopes, plugins, playback policies, and multi-part requirements are clarified and resolved.
