# Feature Specification: Modern Web Interface and UI/UX Redesign

**Feature Branch**: `002-ui-ux-redesign`

**Created**: 2026-09-29

**Status**: Draft

**Input**: User description: "I need a better UI/UX - and a nextjs platform web interface slug=ui-ux-redesign"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cinematic Media Discovery, Filtering & Direct Video Links (Priority: P1)

A user wants an engaging, modern web interface to quickly search movies and series, view rich visual cards with release metadata, filter releases by quality/audio, and access direct download links or video previews cleanly organized by resolution, codec, and language dubbing without pop-ups or visual clutter.

**Why this priority**: Discovering and downloading movies and series is the core utility of the aggregator. A high-contrast visual interface with intuitive quality filtering and one-click link copying transforms scraper output into a premium content portal.

**Independent Test**: Can be tested by searching for a movie title on desktop and mobile, viewing poster artwork, release year, and synopsis, filtering variants by resolution, copying or opening a direct download link, and playing an opportunistic stream preview in under 3 clicks.

**Acceptance Scenarios**:

1. **Given** a user navigates to the web interface, **When** the page loads, **Then** the user sees a cinematic hero search bar with category selectors (Movies, Games, Music), active source badges, and instant visual responsiveness.
2. **Given** the user enters a search query in Persian or English under the Movies category, **When** the query executes, **Then** the interface displays matching titles as media cards featuring high-resolution poster artwork, localized Persian/English titles, release year, category tags, and provenance source indicators.
3. **Given** a selected media item card, **When** the user inspects available download options, **Then** the interface presents distinct, well-labeled badges categorizing links by resolution (480p, 720p, 1080p, 4K), encoding (x264, x265/HEVC), and audio track type (Persian Dubbed, Soft Subtitled, Original).
4. **Given** any movie download variant, **When** the user clicks the download trigger or the copy link icon, **Then** the browser initiates a direct client-to-CDN download or copies the direct URL to the clipboard with positive confirmation, without intermediary ad pop-ups or server proxying.
5. **Given** a movie result with an available direct stream URL, **When** the user clicks the stream preview button, **Then** an inline or modal video player plays the stream directly in-browser.

---

### User Story 2 - Multi-Part Game Archive Management & Batch Link Exporter (Priority: P1)

A gamer searching for repackaged or scene PC/console games needs to see all sequential archive parts clearly organized with individual file sizes, verify the extraction password at a glance, copy individual links or export all part links in a single click for import into external download managers (e.g. IDM, aria2, JDownloader).

**Why this priority**: Game archives commonly span 10 to 50 split RAR files with easily forgotten extraction passwords. Consolidating multi-gigabyte release archives into an ordered, clean list with a one-click clipboard exporter and password copier eliminates high user friction.

**Independent Test**: Can be tested by searching for a game title, opening the game release card, verifying that all parts are listed in strictly increasing numerical order with accurate file sizes, copying the archive password via dedicated copy button, and exporting all part links to the clipboard formatted for download managers.

**Acceptance Scenarios**:

1. **Given** the user is on the Games tab, **When** searching for a game title, **Then** the system presents matching game titles with release details, release group (e.g. FitGirl, ElAmigos), version, total size, and source tags.
2. **Given** a game release result with multi-part archives, **When** the user views the download section, **Then** all archive parts are displayed in sequential order (Part 1, Part 2, ... Part N) alongside their individual file sizes and overall package size.
3. **Given** an archive with an extraction password, **When** viewing the game card, **Then** the password is displayed in a dedicated high-visibility pill element with a one-click copy button providing instant visual confirmation.
4. **Given** an archive list of multiple parts, **When** the user clicks the "Copy All Links" action, **Then** all direct download URLs are copied to the system clipboard separated by newlines, accompanied by a non-intrusive toast notification.
5. **Given** a game archive with non-consecutive or missing parts detected by validation, **When** viewing the release card, **Then** the card displays a prominent warning identifying missing part numbers to prevent incomplete downloads.

---

### User Story 3 - Inline Audio Audition & Direct Music Download (Priority: P2)

A music listener wants to search for Persian and international songs or albums, preview audio immediately using a persistent inline player without navigating away from search results, and download high-quality audio files directly.

**Why this priority**: Audio discovery requires immediate auditioning. Users must be able to verify track quality and performance before downloading.

**Independent Test**: Can be tested by searching for a song or artist, pressing play on an inline audio preview to listen to the stream, verifying that existing playback halts if a new track is started, and selecting between 128kbps and 320kbps download options.

**Acceptance Scenarios**:

1. **Given** the user selects the Music category, **When** searching for an artist or song name, **Then** results render as audio cards displaying album artwork, artist name, track title, and duration.
2. **Given** any listed music track, **When** the user activates the play control, **Then** an audio stream plays directly in the browser with progress scrubber, play/pause toggle, and time display, without refreshing or navigating away from the search page.
3. **Given** active audio playback, **When** the user plays a different track, **Then** the previous track pauses automatically and the new track commences without overlapping audio.
4. **Given** a music track result, **When** viewing download options, **Then** separate buttons for 128kbps and 320kbps MP3 variants are prominently displayed with file size indicators.
5. **Given** an audio track without an active stream preview, **When** rendered, **Then** the card displays a disabled preview state while keeping direct download links active and accessible.

---

### User Story 4 - Accessible, Responsive Bilingual (RTL/LTR) Shell & Keyboard Navigation (Priority: P2)

Users on mobile phones, tablets, and desktop workstations require a fluid, modern interface that respects Persian right-to-left (RTL) reading flow while properly isolating left-to-right (LTR) technical filenames, codecs, and URLs, maintaining high visual contrast in dark and light viewing modes, and supporting keyboard-first navigation.

**Why this priority**: Persian digital media users constantly alternate between Persian text and technical English metadata (codecs, filenames, URLs). Proper bidirectional layout support, touch targets, contrast compliance, and keyboard shortcuts are mandatory for frictionless usability.

**Independent Test**: Can be tested on viewports from 375px (mobile) to 1440px (desktop), verifying RTL alignment for Persian descriptions, LTR alignment for file paths/specs without punctuation inversion, keyboard shortcut `/` to focus search, visible focus rings, and dark theme contrast exceeding 4.5:1.

**Acceptance Scenarios**:

1. **Given** any screen size from mobile (375px) to desktop (1440px+), **When** interacting with the application, **Then** layout structures reflow seamlessly without horizontal scrollbars, preserving minimum 44x44px touch targets on mobile devices.
2. **Given** Persian titles and descriptions mixed with English technical specs (e.g. `1080p.x265.10bit-PSA`), **When** content is rendered, **Then** Persian text reads naturally Right-to-Left while technical identifiers, version numbers, and filenames retain strictly isolated Left-to-Right formatting with no inverted brackets or punctuation.
3. **Given** a user pressing `/` or `Ctrl+K` / `Cmd+K` anywhere on the page, **When** the shortcut is triggered, **Then** the main search input immediately receives focus with prior text selected for quick replacement.
4. **Given** a user navigating entirely via keyboard, **When** tabbing through interactive elements (inputs, category tabs, download buttons, audio controls), **Then** each active element displays an unambiguous, high-contrast visual focus ring.
5. **Given** default dark mode display, **When** viewing any surface, **Then** standard body text adheres to a minimum 4.5:1 contrast ratio against card and canvas backgrounds.

---

### Edge Cases

- **Zero Search Results**: When a search query yields no matches from any upstream source, the interface displays an informative empty state suggesting alternative keywords, Persian spelling variations, or category switching, rather than an empty blank screen or technical error code.
- **Upstream Source Latency or Timeout**: If one or more upstream media portals fail to respond within their allotted timeout budget (7s per source, 10s global), the interface displays partial results from responding sources alongside dismissible warning pills identifying which sources timed out.
- **Mixed Content (HTTP Download Links on HTTPS Web Client)**: Because upstream Iranian CDNs frequently serve media over plain `http://`, the web client MUST initiate downloads via direct link navigation (`<a href="..." download rel="noopener noreferrer">`) and provide one-click link copying, ensuring browser security policies do not silently block media downloads or trigger cross-origin errors.
- **Clipboard API Denial or Insecure Context**: If the browser denies clipboard access or runs in a restricted context, clicking "Copy Link" or "Copy All Links" falls back to presenting a pre-selected modal textarea with a clear "Press Ctrl+C to copy" prompt.
- **Very Long Release Names & Truncation**: When titles or filenames exceed 80 characters (e.g. multi-edition repacks with extensive DLC lists), text is gracefully truncated with an ellipsis and reveals the full string on hover or card expansion without breaking layout bounds.
- **Rapid Category or Query Switching**: When a user rapidly changes search tabs or submits a new query before a prior search finishes, prior asynchronous fetch requests are aborted so obsolete responses never overwrite newer query results.
- **Missing or Corrupted Archive Parts**: If a multi-part archive sequence is missing an intermediate part (e.g. Part 1, Part 3 without Part 2), the interface highlights the missing sequence in a prominent warning state to prevent users from downloading broken archives.
- **Unavailable Audio Stream**: If an upstream music source provides download links but a broken preview stream, the inline player displays an honest "Stream preview unavailable" badge while keeping direct download options accessible.
- **Cache Invalidation / Force Refresh**: Users can trigger a fresh scrape via a dedicated "Refresh" action button on the search results view to bypass cached or database results when updated episodes or parts are expected.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated modern web interface allowing users to search, filter, and inspect media across Movies, Games, and Music categories.
- **FR-002**: System MUST render categorized search tabs allowing users to switch category context while retaining the active search query text.
- **FR-003**: System MUST display media search results as rich content cards containing title, localized Persian/English names, thumbnail/poster imagery, release year, category tags, and provenance source indicators.
- **FR-004**: System MUST group movie and series download links by quality attributes (resolution, video codec, audio dubbing, subtitle format) so users can distinguish formats at a glance.
- **FR-005**: System MUST provide an opportunistic video stream player for movie results that contain a verified direct `stream_url`.
- **FR-006**: System MUST validate and present multi-part game archives in strictly sequential order with individual part sizes and aggregate download size.
- **FR-007**: System MUST detect and visually flag non-consecutive or missing archive parts within a game release package.
- **FR-008**: System MUST prominently display game archive extraction passwords with a dedicated one-touch clipboard copy control.
- **FR-009**: System MUST provide a "Copy All Links" action on multi-part game packages that copies all direct URLs into the system clipboard separated by newlines, formatted for download managers.
- **FR-010**: System MUST provide an individual copy-link action on every downloadable asset (movie variant, game part, music track) with instant visual feedback.
- **FR-011**: System MUST provide a persistent inline audio preview player on music search results supporting play, pause, progress scrubbing, volume control, and single-track exclusive playback.
- **FR-012**: System MUST ensure that initiating any media stream or file download triggers a direct client-to-CDN connection without buffering, proxying, or relaying media content through the aggregator application server (Constitution Principle III).
- **FR-013**: System MUST support bidirectional typography and layout, rendering Persian content in Right-to-Left (RTL) flow while strictly isolating Left-to-Right (LTR) orientation for technical terms, filenames, hashes, and URLs.
- **FR-014**: System MUST display non-blocking skeleton loaders during query processing and clear status banners when upstream sources experience timeouts or degraded connectivity.
- **FR-015**: System MUST provide global keyboard navigation, including `/` or `Ctrl+K` / `Cmd+K` to focus the search bar, `Escape` to close drawers/modals, and visible focus rings on all interactive elements.
- **FR-016**: System MUST expose and consume structured backend API endpoints (`/api/search`, `/api/sources`, `/api/health`) returning standardized JSON payloads.
- **FR-017**: System MUST provide an in-view filter bar allowing users to filter loaded search results by resolution (4K, 1080p, 720p, 480p), audio type (Dubbed, Subtitled), and scraper source.
- **FR-018**: System MUST provide a manual "Force Refresh" action on search result pages to bypass server/database cache and fetch fresh scrape data from enabled upstream sources.

### Key Entities

- **MediaItem**: Canonical aggregated media item containing unique ID, title, localized Persian/English names, category (`movies`, `games`, `music`), source identifier, original page URL, release year, poster/cover URL, description, and category-specific variant payloads.
- **MovieDownloadVariant**: Specific downloadable movie/series file asset containing quality label (e.g. 1080p, 720p), video codec (e.g. x265, x264), audio track language/type (e.g. Persian Dubbed, Soft Subtitled), direct upstream CDN download URL, file size in MB, and source name.
- **GameRelease**: Specialized game release package containing release group (e.g. FitGirl, ElAmigos), version, total package size, archive extraction password, ordered list of `GamePartLink` entities, missing parts flag, and missing part numbers list.
- **GamePartLink**: Individual archive part link containing part number (1-based integer), part label (e.g. "Part 1"), direct upstream download URL, and individual file size string.
- **MusicTrack**: Audio track entity containing track title, artist name, album name, cover artwork URL, optional direct preview stream URL, and bitrate download variants list.
- **MusicDownloadVariant**: Audio quality download option containing bitrate specification (e.g. "320kbps", "128kbps"), direct download URL, and file size string.
- **SearchQuery**: Search request state containing raw query string, normalized Unicode NFKC Persian query string, selected category, and optional extracted release year.
- **SourceStatus**: Scraper source health record containing source ID, display name, category, enabled status, primary base URL, and recent response status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Cached search results render first meaningful paint in under 1.5 seconds; fresh multi-source search results display progressive skeleton feedback within 500ms and complete within the 10-second global scraper deadline.
- **SC-002**: 95% of users can locate and initiate their preferred format download or stream within 3 clicks or taps from search submission.
- **SC-003**: 100% of multi-part game packages offer a single-click action that copies all part links to the clipboard formatted for download managers.
- **SC-004**: 100% of individual download links provide a 1-click copy URL button with visual confirmation.
- **SC-005**: 100% of interactive controls and text meet WCAG 2.1 AA accessibility standards, including minimum 4.5:1 text contrast and minimum 44x44px mobile touch target dimensions.
- **SC-006**: 100% of audio previews play directly within the active view without triggering page navigation or modal interruption, with strict single-track playback enforcement.
- **SC-007**: 0% of media payloads are relayed or buffered through the aggregator application server, verifying total adherence to the direct-to-client CDN constraint (Constitution Principle III).
- **SC-008**: 100% of technical filenames, release hashes, codecs, and URLs render with correct LTR formatting inside Persian RTL layouts with 0 bidirectional punctuation inversion defects.

## Assumptions

- The modern web interface will reside within the monorepo workspace (`apps/web`) using a modern React/Next.js stack, alongside the Python backend service (`apps/api`).
- **Constitution Amendment**: Constitution Principle II (Simplicity/YAGNI) is amended from server-rendered Jinja2 templates to a Next.js web application consuming the FastAPI backend over JSON API endpoints, in order to fulfill the rich interactive requirements (audio player, copy-all clipboard, instant filtering, and responsive bilingual UX). Constitution Principle III (Zero Media Relaying) remains inviolable.
- The backend application server exposes structured JSON endpoints (`/api/search`, `/api/sources`, `/api/health`) with CORS enabled for the frontend application.
- Upstream media hosts and CDNs permit direct cross-origin media playback and browser file downloads from user IP addresses.
- Users access the application using modern evergreen web browsers (Chrome, Firefox, Safari, Edge) with native HTML5 audio/video, CSS Flexbox/Grid, and Clipboard API support.
- Initial release focuses on a dark-first theme tailored for entertainment and media consumption, with full RTL/LTR bidirectional support.
