# Feature Specification: Iranian Multi-Media Direct Link Aggregator (MVP)

**Feature Branch**: `001-mvp`

**Created**: 2026-09-27

**Status**: Implemented (MVP) - Primary categories Games & Music live; Movies honest empty state pending active mirror domains

**Input**: User description: "slug=mvp - Problem: Persian-speaking internet users face extreme friction finding clean media links across fragmented Iranian websites due to invasive pop-under ads, broken domains, confusing multi-part game downloads, and scattered format options. Chosen approach: Option A — Pluggable Multi-Media Direct Link Aggregator. A fast web application with explicit category tabs (Movies, Games, Music), a modular scraper plugin engine for targeted Iranian portals, category-specific metadata resolution, structured split-archive presentation for games, and inline audio playback for music."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Search and Download Movies/Series by Format (Priority: P1)

A user wants to find and download a specific movie or series with a localized Persian dub or subtitle track, without navigating deceptive ad buttons or redirect loops.

**Why this priority**: Movie and TV series discovery is the primary entry point for Iranian media search and delivers immediate value as a standalone utility.

**Independent Test**: Can be fully tested by entering a movie title query, receiving categorized direct links (resolution, codec, dub/sub), and clicking a link to initiate a direct file download.

**Acceptance Scenarios**:

1. **Given** the user selects the "Movies" category tab, **When** the user searches for a movie title (in English or Persian), **Then** the system presents matching media items with title, release year, poster, and available format variants.
2. **Given** a selected movie result, **When** format options are displayed, **Then** download links are clearly segmented by resolution (480p, 720p, 1080p, 4K), encoding (x264, x265/HEVC), and audio/subtitle status (Persian dubbed, soft-subbed, or original audio).
3. **Given** a displayed download link, **When** the user clicks the link, **Then** the browser directly begins downloading the media file from the upstream source without intermediate pop-ups or third-party advertising pages.

---

### User Story 2 - Complete Multi-Part Game Archive Extraction (Priority: P1)

A gamer wants to download a large PC or console game repack split across multiple archive parts without missing parts or losing the archive extraction password.

**Why this priority**: Game downloads represent high friction due to 20–80GB releases split into 10–40 RAR parts with obscure archive passwords. Delivering clean, ordered parts with a one-click copy tool provides massive user utility.

**Independent Test**: Can be fully tested by searching for a game title, receiving an ordered list of part links (Part 1 through Part N) with file sizes, verifying the archive password is shown, and using the one-click action to copy all links.

**Acceptance Scenarios**:

1. **Given** the user selects the "Games" category tab, **When** the user searches for a game title, **Then** the system returns matching game releases from supported gaming portals.
2. **Given** a game release result, **When** the user expands the download section, **Then** all archive parts are listed in strict sequential order (Part 1, Part 2, ... Part N) with individual part file sizes and the total archive size.
3. **Given** an archive with an extraction password, **When** the game details are displayed, **Then** the archive password is prominently displayed with a one-click copy button.
4. **Given** a multi-part game release, **When** the user clicks "Copy all links", **Then** all part URLs are copied to the system clipboard formatted for immediate import into download managers.

---

### User Story 3 - Music Track Discovery, Preview, and Download (Priority: P1)

A music listener wants to find a Persian track or album, listen to a preview instantly in the browser, and download the high-bitrate MP3 directly.

**Why this priority**: Music queries have distinct user expectations — instant audio playback without page navigation, plus quick access to 128kbps and 320kbps MP3 files.

**Independent Test**: Can be fully tested by searching for an artist or song name, pressing play on the inline audio player to hear the track, and clicking the 320kbps download button to save the MP3.

**Acceptance Scenarios**:

1. **Given** the user selects the "Music" category tab, **When** the user searches for a song, artist, or album name, **Then** matching tracks are listed with cover art, artist name, and track title.
2. **Given** a listed music track, **When** the user clicks the play button on the inline audio player, **Then** the audio streams directly in the browser without redirecting or navigating away.
3. **Given** a listed music track, **When** download options are viewed, **Then** direct download links are provided for standard bitrates (128kbps and 320kbps) with corresponding file sizes.

---

### User Story 4 - Opportunistic Movie Streaming (Priority: P2)

A user searching for a movie wants to watch it directly in the web browser if the upstream video host permits unproxied playback.

**Why this priority**: Enhances the movie discovery experience for users on mobile or casual viewers, while cleanly falling back to download buttons when upstream CORS or hotlink protections prevent direct browser playback.

**Independent Test**: Can be tested by searching for a movie where upstream provides an unblocked video stream URL; the embedded video player loads and plays the stream.

**Acceptance Scenarios**:

1. **Given** a movie result where an upstream source provides an unauthenticated, browser-playable video stream, **When** the user views the movie result, **Then** an embedded video player is made available alongside download links.
2. **Given** a movie result where upstream video streams enforce restrictive hotlinking or browser playback blocks, **When** the user views the movie result, **Then** the system omits the broken embedded player and presents clean direct download buttons with zero player error screens.

---

### User Story 5 - Extensible Source Portal Management (Priority: P2)

An operator wants to add support for a new Iranian download website or update an existing website's domain mirror without modifying core aggregation logic.

**Why this priority**: Iranian portals frequently change domains due to anti-filtering measures. Making sources modular and domain configurations externalized ensures long-term operational resilience.

**Independent Test**: Can be tested by registering a new source configuration or updating a domain mirror, verifying the system immediately queries the new endpoint.

**Acceptance Scenarios**:

1. **Given** an operator configures an updated base domain for a target portal, **When** subsequent searches are performed, **Then** the system uses the new base domain and continues extracting links seamlessly.
2. **Given** an upstream portal redirects an HTTP request to a new mirror domain (via 301/302 redirects), **When** the scraper queries the site, **Then** the system follows the redirect automatically and captures the active working domain.

---

### Edge Cases

- **Upstream Portal Outage**: If one or more source sites fail to respond or time out during a search, the system MUST still return results from healthy sources and display a non-intrusive warning indicating which sources were temporarily unavailable.
- **Complete Zero-Results Scenario**: If no sources return results for a query, the system MUST display a clear "No results found" message with suggestions (e.g. check spelling, try original English or Persian title).
- **Missing Game Archive Parts**: If a source site has incomplete or missing split parts (e.g. Parts 1, 2, and 4 present, but Part 3 missing), the system MUST visually highlight the missing part gap rather than silently renumbering parts.
- **Mixed Persian/English Queries**: If a user inputs mixed scripts, transliterated names, or release years (e.g. "Inception 2010" or "تلقین"), the system MUST normalize and match the title across both English and Persian releases.
- **Link Expiration & Stale Caching**: If upstream links use short-lived session tokens, the cache TTL MUST automatically expire within 30–60 minutes, ensuring users do not receive expired 403 download URLs.
- **Malicious or Parked Domain Redirects**: If an upstream portal domain expires and redirects to an unrelated ad/parked landing page, the scraper MUST detect non-matching page signatures and abort without serving junk links to the user.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide three distinct category tabs in the interface: "Movies", "Games", and "Music".
- **FR-002**: System MUST isolate search queries, metadata resolution, and scraper execution to the currently active category tab.
- **FR-003**: System MUST provide a search input supporting Persian and English text queries and optional release years.
- **FR-004**: System MUST enrich search results with descriptive metadata (cover/poster art, release year, genre, artist/developer) using category-specific sources.
- **FR-005**: System MUST implement a pluggable source architecture where individual scrapers operate as decoupled modules conforming to a unified search and extraction interface.
- **FR-006**: System MUST support initial source scrapers for Movies: Film2Media, AvaMovie, Zarfilm, and MoboMovie.
- **FR-007**: System MUST support initial source scrapers for Games: YasDL, Downloadha, and Game2DL / PersianDL.
- **FR-008**: System MUST support initial source scrapers for Music: Nex1Music, Pop-Music, RadioJavan, and UpMusic.
- **FR-009**: System MUST execute source scrapers concurrently for the active category, enforcing a global timeout budget so slow sources do not degrade total search latency.
- **FR-010**: System MUST parse and categorize movie download links by video resolution (480p, 720p, 1080p, 4K), video codec (x264, x265/HEVC, 10-bit), and audio language track (Persian dubbed vs Persian soft-subbed vs original audio).
- **FR-011**: System MUST present direct download buttons for all extracted movie formats that directly initiate upstream downloads on click.
- **FR-012**: System MUST provide an opportunistic in-browser video player when an upstream movie stream URL is verified to be directly playable without CORS blocks.
- **FR-013**: System MUST omit in-browser video players and fall back cleanly to download buttons when upstream video streams are blocked or require proxying.
- **FR-014**: System MUST parse game download archives into an ordered sequence of parts (Part 1 through Part N) with individual part sizes and aggregate download size.
- **FR-015**: System MUST extract and prominently display game archive extraction passwords associated with each download release.
- **FR-016**: System MUST provide a one-click "Copy all links" action on multi-part game releases that copies all URLs formatted for download manager batch queues.
- **FR-017**: System MUST parse music results into standardized bitrate tiers (128kbps and 320kbps MP3s) with exact file sizes.
- **FR-018**: System MUST provide an integrated inline HTML5 audio preview player allowing instant browser playback of direct MP3 links.
- **FR-019**: System MUST provide direct download buttons for music tracks that initiate file downloads directly in the user's browser.
- **FR-020**: System MUST automatically follow HTTP 301 and 302 redirects when querying source websites to accommodate live domain shifts.
- **FR-021**: System MUST support externalized configuration for source base URLs allowing domain updates without codebase changes.
- **FR-022**: System MUST cache search results and extracted download links with a configurable short time-to-live (30 to 60 minutes) to avoid redundant scraping while preventing expired download link tokens.
- **FR-023**: System MUST restrict extraction strictly to publicly available, unauthenticated download links without bypassing paid VIP walls or credential requirements.
- **FR-024**: System MUST NOT store, host, or relay video/audio media files or game archives through its own servers.

### Key Entities

- **Category**: The high-level media classification (`Movies`, `Games`, `Music`).
- **Source**: A configured target portal entity containing an identifier, name, category, active base URL(s), and enabled status.
- **SearchQuery**: An incoming search request containing the raw query string, normalized query string, target category, and timestamp.
- **MediaItem**: A discovered title entity containing title (Persian and English), category, release year, poster/cover image URL, description, and source portal attribution.
- **MovieDownloadVariant**: A specific movie file variant containing resolution, codec, audio language track, file size, direct download URL, and source portal name.
- **GameRelease**: A game download package containing release group (e.g. FitGirl, DODI, ElAmigos), total file size, archive extraction password, and an ordered list of part links.
- **GamePartLink**: A single segment of a split game archive containing part index (1..N), file size, and direct download URL.
- **MusicTrack**: An audio track entity containing song title, artist, album, cover art, direct stream preview URL, and download links for 128kbps and 320kbps bitrates.
- **CachedResult**: A stored search result bundle containing the cache key (category + normalized query), extracted media items, timestamp, and time-to-live expiry.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Repeat searches for the same query within the active cache window display complete results in under 2 seconds.
- **SC-002**: Initial uncached searches across all healthy category sources complete and render results in under 12 seconds.
- **SC-003**: Greater than 80% of top 100 popular movie, game, and music queries successfully surface at least one valid, clickable direct download link.
- **SC-004**: Greater than 90% of rendered direct download links successfully initiate file downloads without immediate HTTP 403 or 404 errors.
- **SC-005**: 100% of multi-part game archives display parts in correct sequential numerical order and correctly show the archive password when present on the source page.
- **SC-006**: A new source portal can be added to any category by introducing a single decoupled scraper module and configuration entry without modifying search or UI logic.
- **SC-007**: Zero server bandwidth is consumed by video or audio relaying; all downloads and playable streams connect directly from the user's client to upstream CDNs.

## Assumptions

- Target Iranian media portals maintain public, unauthenticated download tiers for popular releases that do not require active VIP accounts.
- Upstream download URLs do not strictly enforce IP-binding to the scraper's requesting IP, permitting end users to initiate direct downloads from their own browser IPs.
- Music MP3 links hosted by Iranian music blogs do not enforce restrictive CORS headers, permitting direct in-browser playback via standard HTML5 `<audio>` elements.
- Target website DOM structures and CSS selectors remain reasonably consistent between minor site updates, with major domain changes communicating via HTTP 301/302 redirects.
- Users access the application via modern standards-compliant web browsers supporting HTML5 audio and video playback.
- No specialized CAPTCHA-solving infrastructure or headless browser farms are required for the initial MVP sources.
