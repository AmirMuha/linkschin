# Idea Intake: Iranian Media Fetcher (Movies, Games & Music)

- **Slug**: idea
- **Created**: 2026-09-27
- **Source**: pasted text
- **Type**: new-capability

## Idea (as captured)

> "give your intake and research for a movie-fetcher website, the goal of this idea is to find the websites streaming the searched movie by the user and provide the user with direct links to download the movie in different formats if available, or a direct link to stream the movie online for user. my target for the mvp is iranian movie websites, not also for movies but also for games,musics as well"

## Restated

A unified web application that allows users to search across Iranian websites for movies, games, and music, surfacing direct download links categorized by format/quality/part and providing in-browser direct streaming links where available (for movies and audio).

## Origin & Context

- **Raised by**: amirmuha
- **Trigger**: Scope expansion from movie-only aggregator to an Iranian multi-media aggregator covering movies, PC/console games, and music.

## First-Glance Unknowns (All Resolved)

- **Search Interface**: Explicit category tabs (`Movies`, `Games`, `Music`) to segment search queries, scraper dispatch, and metadata models cleanly.
- **Pluggable Architecture**: Modular scraper plugin architecture across all categories allowing new source websites to be added with minimal configuration.
  - **Movies Plugins**: Film2Media, AvaMovie, Zarfilm, MoboMovie.
  - **Games Plugins**: YasDL, Downloadha, Game2DL / PersianDL.
  - **Music Plugins**: Nex1Music, Pop-Music, RadioJavan, UpMusic.
- **Game Download Structure**: Support for split RAR archives (Part 1, Part 2...), individual part file sizes, archive passwords, and a "Copy all links" button for download managers.
- **Music Playback**: Integrated HTML5 `<audio>` player for streaming 128kbps/320kbps MP3 tracks in-browser alongside direct download buttons.
- **Movie Streaming Policy**: Opportunistic streaming — play directly in browser if CORS/stream link permits, otherwise display direct download options (no server-side media proxy).
- **Metadata APIs**: Category-specific metadata enrichment (TMDB for movies, RAWG/IGDB for games, native site metadata/ID3 for music).
- **Access Level**: Free public tiers only (no VIP account pooling or paywall bypass).
- **Anti-Bot & Domain Churn**: Lightweight HTTP client with custom headers, cookie handling, automatic 301/302 redirect tracking, and configurable base domain overrides.
- **Link Expiration & Caching**: On-demand real-time fetching with short in-memory cache TTL (30–60 minutes).
