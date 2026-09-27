# Idea Research: Iranian Media Fetcher (Movies, Games & Music)

- **Slug**: idea
- **Created**: 2026-09-27
- **Evidence confidence (overall)**: medium

## Users & Demand

- **Movies**: Persistent demand for ad-free direct download links (720p/1080p x265 with Persian dub/sub tracks) due to domestic intranet traffic pricing and bandwidth stability. Mobile viewers appreciate opportunistic direct streaming. — [ASSUMPTION] (confidence: high)
- **Games**: Heavy demand among Iranian PC/console gamers for direct multi-part downloads (FitGirl/DODI repacks, updates). International stores (Steam/PlayStation Network) face throttling, filtering, or payment barriers. Gamers routinely download 20–80GB archives split into 2GB parts and need clean link lists with passwords. — [ASSUMPTION] (confidence: high)
- **Music**: High volume of search for Persian pop, traditional, and indie music singles and albums. Users want direct 320kbps MP3 download links and instant audio preview playback without pop-ups or redirect gates. — [ASSUMPTION] (confidence: high)

## Prior Art

- **Telegram Media Search Bots**: Succeeded across movies and music with conversational search and direct file delivery, but suffer from copyright bans and lack structured multi-part game archive handling. — [precedent analysis | ASSUMPTION]
- **Kodi / Stremio Community Addons**: Demonstrated pluggable scraper model for movies and series, but prone to scraper rot when DOM structures change. — [precedent analysis | ASSUMPTION]
- **Iranian Download Portals (YasDL, Downloadha, Soft98)**: Decades of precedent proving high traffic for direct HTTP downloads of games and software with split archives and standard passwords. — [precedent analysis | ASSUMPTION]
- **Iranian Music Portals (Nex1Music, Pop-Music, RadioJavan)**: Standardized around direct MP3 hosting (128k/320k) with simple URL structures and low CORS restrictions. — [precedent analysis | ASSUMPTION]

## Market & Context

- **Current User Workarounds**: Users juggle 5–10 specialized bookmarks across categories, deal with aggressive pop-unders and betting advertisements, copy multi-part game links one-by-one into download managers (IDM), and hunt for archive extraction passwords.
- **Publisher Dynamics**: Scraped sites rely on display advertising. An aggregator delivering clean links bypasses ads, requiring robust scraper design against anti-scraping and domain migration.

## Data & Constraints

- **Domain Churn**: High across movie sites (filtered every 1–4 weeks); moderate across music and game sites. Requires automatic HTTP 301/302 redirect tracking and configurable domain overrides.
- **Game Multi-Part Archives**: A single PC game release can feature 5 to 40 split `.part01.rar` to `.partN.rar` download links. Scrapers must parse part indices, individual file sizes, total size, and archive passwords (e.g. `www.yasdl.com`, `www.downloadha.com`).
- **Music Audio Streaming**: Unlike video streams with complex HLS/CORS requirements, direct MP3 links on music sites are lightweight and standard-compliant, functioning reliably inside an HTML5 `<audio>` player without proxying.
- **Movie In-Browser Streaming**: Opportunistic only; without a heavy video proxy, CORS-protected or tokenized video streams fall back to direct download buttons.
- **Metadata Normalization**: Requires category-specific metadata APIs: TMDB for movies/series, RAWG/IGDB for games, and native target site scraping/ID3 tags for music.
- **Access Level**: Restricted strictly to free, public download tiers.

## Evidence Against the Idea

- **Scraper Maintenance Across 3 Domains**: Expanding from 1 category (movies) to 3 (movies, games, music) triples the scraper surface area. Changes in site layout across any of the 8+ target portals require scraper updates.
- **Multi-Part Link Fragility**: If an upstream game portal changes its CDN host or part naming convention, partial link sets can break game installation for users.
- **Hosting & TOS Risks**: Indexing copyrighted games, movies, and music increases exposure to DMCA takedown notices on mainstream hosting providers.

## Gaps & Open Questions (Resolved)

- **Search Segmentation**: Resolved — UI will feature explicit category tabs (`Movies`, `Games`, `Music`).
- **Target Site Plugins**: Resolved — Pluggable architecture starting with:
  - Movies: Film2Media, AvaMovie, Zarfilm, MoboMovie.
  - Games: YasDL, Downloadha, Game2DL / PersianDL.
  - Music: Nex1Music, Pop-Music, RadioJavan, UpMusic.
- **Multi-Part Games**: Resolved — Structured part list with sizes, passwords, and "Copy all links" button.
- **Audio Playback**: Resolved — Integrated inline HTML5 audio player for 128k/320k MP3s.
- **Movie Streaming**: Resolved — Opportunistic browser playback where CORS permits; direct download buttons otherwise (no media proxy).
- **Metadata**: Resolved — Category-specific APIs (TMDB, RAWG/IGDB, native).
- **Caching**: Resolved — Real-time on-demand scraping with 30–60 minute cache TTL.

## Sources

- *Synthesized from Iranian media download ecosystem patterns, web standards, and user clarification answers.*
