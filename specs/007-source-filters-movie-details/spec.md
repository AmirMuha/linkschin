# Feature Specification: Source Tier Filtering, Censorship Metadata, and IMDb Ratings

**Feature Branch**: `007-source-filters-movie-details`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "add some filters to filter the websites based on them being free or premium, also I need details on whether the movie is censored or not. the IMDB rating of the movie on each card."

## Clarifications

### Session 2026-09-30

- Q: How should the "Free Sources Only" filter treat freemium websites that offer both free standard-definition links and paid VIP high-definition links? → A: Include freemium sources in results, but filter their download matrix to show only free links.
- Q: How should the search filter handle items with "Unspecified" censorship status when a user selects the "Uncensored Only" filter? → A: Exclude unspecified titles from "Uncensored Only" results (strict verification; unverified items appear only under "All").
- Q: When an upstream source page does not provide an IMDb score in its HTML metadata, how should the system handle the missing rating? → A: Display an unrated fallback badge ("—" / "بدون امتیاز") without calling third-party APIs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Filtering Media Sources by Access Tier (Free vs. Premium) (Priority: P1)

A media consumer searching for movies wants to quickly exclude sources that require paid VIP accounts or subscription logins, while another user holding VIP accounts wants to prioritize premium sources for faster transfer speeds. From the search results view, the user selects an access filter ("All Sources", "Free Sources Only", or "Premium Sources Only"). The search results immediately refine to show only items matching the selected source tier. For freemium sources, selecting "Free Sources Only" preserves the movie card in results while filtering its download matrix to display only free variants.

**Why this priority**: Essential to saving users time and eliminating frustration when attempting to download links from sources requiring paid memberships they do not possess.

**Independent Test**: Can be fully tested by executing a search query, toggling the access tier filter to "Free Sources Only", and verifying that all displayed movie cards originate from free or freemium sources (with freemium cards displaying only free variants), while purely premium sources are hidden.

**Acceptance Scenarios**:

1. **Given** a search query returning results from free, freemium, and premium sources, **When** the user selects the "Free Sources Only" filter, **Then** free sources and freemium sources remain visible, freemium download matrices display only free links, and purely premium sources are hidden.
2. **Given** the search results view, **When** the user selects the "Premium Sources Only" filter, **Then** purely premium sources and freemium sources with VIP options remain visible, displaying VIP download variants.
3. **Given** any movie card displayed in the results, **When** rendered, **Then** it presents a distinct badge or tag indicating whether the source is Free, Premium, or Freemium.

---

### User Story 2 - Censorship Status Visibility and Filtering (Priority: P2)

A media consumer wants to know before downloading whether a movie or TV series has been edited or censored according to local regulatory guidelines, or if it represents an untouched full-length release. Each movie card clearly displays its censorship status (Censored vs. Uncensored), and users can filter search results to see only uncut versions or only family-friendly/censored versions.

**Why this priority**: Censorship is a decisive factor for Iranian media consumers; users specifically look for either uncut full editions or censored releases for family viewing.

**Independent Test**: Can be fully tested by performing a movie search, verifying the presence and accuracy of censorship badges on movie cards, and toggling the censorship filter to confirm that only matching titles/variants are displayed.

**Acceptance Scenarios**:

1. **Given** search results containing censored and uncensored titles, **When** the user views the result grid, **Then** each movie card displays an unambiguous badge indicating "نسخه کامل / بدون سانسور" (Uncensored) or "بازبینی شده / سانسور شده" (Censored).
2. **Given** the user wants to see only uncut releases, **When** they activate the "بدون سانسور" (Uncensored Only) filter, **Then** any movie or variant flagged as censored or unspecified is filtered out.
3. **Given** a movie where an upstream source offers both censored and uncensored download variants, **When** the user inspects the download matrix, **Then** each variant row specifically indicates its censorship state.
4. **Given** an upstream source where censorship cannot be determined from metadata, **When** displayed, **Then** the system displays a neutral "نامشخص" (Unspecified) indicator rather than making a false assertion, and includes the item only when the filter is set to "All".

---

### User Story 3 - IMDb Rating Display on Movie Cards (Priority: P3)

A media consumer browsing search results wants to assess movie quality and audience acclaim at a glance without having to open external websites or check separate databases. Each movie card features a prominent IMDb rating badge directly on or beside the poster artwork.

**Why this priority**: IMDb scores provide instant social proof and quality context, allowing users to make immediate viewing decisions directly from the aggregator card grid.

**Independent Test**: Can be fully tested by running a search for a well-known movie, confirming that the IMDb rating (e.g., "⭐ 7.8") is prominently displayed on the card header/overlay, and verifying that unrated films render an elegant placeholder.

**Acceptance Scenarios**:

1. **Given** a movie result with a recorded IMDb score (e.g., 8.4), **When** the card renders in the search results grid, **Then** an IMDb badge showing the star icon and score `8.4` is clearly visible on the poster overlay.
2. **Given** a movie result without an available IMDb score in upstream metadata, **When** the card renders, **Then** a clean fallback indicator (e.g., "—" or "بدون امتیاز") is displayed directly without invoking third-party APIs or disrupting card layout.
3. **Given** multiple movie cards on a responsive screen (mobile and desktop), **When** viewed across different screen resolutions, **Then** the IMDb score remains consistently positioned, legible, and visually balanced with other metadata badges.

---

### Edge Cases

- **Freemium Sources with Mixed Variant Access**: An upstream source provides free access to standard definition (480p/720p) links, but restricts high-definition (1080p/4K) links to VIP subscribers. The system labels the source as "Freemium" and badges individual variants as either "Free" or "VIP". When the "Free Sources Only" filter is active, freemium items remain visible but their VIP download links are hidden from their download matrix.
- **Mixed Censorship on a Single Movie Entry**: An upstream source lists both censored and uncensored versions on the same page. The card displays a "Mixed / شامل هر دو نسخه" badge, and individual download variants are labeled accordingly; applying a specific censorship filter displays only the matching download links within that card.
- **Unknown / Unspecified Censorship**: When upstream sources do not specify censorship metadata, items are marked `unspecified` and are excluded from strict `Uncensored Only` and `Censored Only` filters, appearing only when `All` is selected.
- **Unrated or Pre-Release Media**: A newly announced film or niche domestic release has no IMDb rating. The card displays an unrated placeholder without layout shift or broken graphic elements.
- **Zero Results After Applying Combined Filters**: A user applies both "Free Only" and "Censored Only" filters on a search query where no sources match both criteria. The system renders an informative empty-state message explaining that no items match the combined filters, with a 1-click option to reset or broaden filter criteria.
- **Malformed or Non-Standard Rating Formats**: An upstream website formats ratings as `84%`, `4.2/5`, or text descriptions. The parser normalizes valid scores into standard 10-point scale decimal representations (`8.4`) or gracefully marks them unrated if parsing fails.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST categorize every upstream source by its access tier: `free`, `premium`, or `freemium`.
- **FR-002**: System MUST provide an accessible filter control on the search results interface allowing users to filter by source access tier (`All`, `Free Only`, `Premium Only`). When `Free Only` is active, freemium sources MUST remain visible with their download matrices filtered to free links only.
- **FR-003**: System MUST display an access tier badge on each movie card and on download variants originating from premium or freemium sources.
- **FR-004**: System MUST extract and persist censorship metadata (`censored`, `uncensored`, `mixed`, or `unspecified`) for movie items and individual download variants.
- **FR-005**: System MUST render a visible, localized censorship badge on each movie card header or metadata section.
- **FR-006**: System MUST provide a filter control on the search results interface allowing users to filter by censorship status (`All`, `Uncensored Only`, `Censored Only`). When `Uncensored Only` or `Censored Only` is active, titles with `unspecified` censorship MUST be excluded to ensure strict verification.
- **FR-007**: When a movie item includes multiple download variants with differing censorship states, each variant row MUST explicitly declare whether it is censored or uncensored.
- **FR-008**: System MUST extract and record the numeric IMDb rating (on a standard 0.0 to 10.0 scale) for each movie item when available in source metadata.
- **FR-009**: System MUST display the IMDb rating prominently on each movie card, accompanied by an established rating icon.
- **FR-010**: System MUST render a graceful fallback indicator ("—" / "بدون امتیاز") when an IMDb rating is unavailable in upstream source metadata, without invoking external third-party lookup services.
- **FR-011**: Filtering by access tier and censorship status MUST operate client-side on fetched search results with instant visual response without requiring redundant backend queries.
- **FR-012**: Filter selections MUST be reflected in URL query parameters so users can bookmark, refresh, or share filtered search result views.

### Key Entities *(include if feature involves data)*

- **SourceAccessTier**:
  - `tier`: Value enum (`free`, `premium`, `freemium`).
  - `label`: Localized display name (e.g., "رایگان", "اشتراکی / VIP", "ترکیبی").
  - `description`: Explanatory tooltip for users.

- **CensorshipStatus**:
  - `status`: Value enum (`uncensored`, `censored`, `mixed`, `unspecified`).
  - `label`: Localized display name (e.g., "بدون سانسور", "سانسور شده", "شامل هر دو نسخه", "نامشخص").
  - `color_token`: Visual theme color associated with the status badge (e.g., emerald for uncensored, amber for censored).

- **MediaItem (Extensions)**:
  - `imdb_rating`: Floating-point numeric rating between 0.0 and 10.0, or null if unrated.
  - `censorship_status`: Overall censorship state of the media item.
  - `source_access_tier`: Access requirement tier of the source providing the item.

- **MovieDownloadVariant (Extensions)**:
  - `is_censored`: Optional boolean indicating whether this specific download file is censored.
  - `is_premium`: Boolean flag indicating if this specific download file requires a paid VIP account.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can toggle source access tier filters and see search results update in under 50 milliseconds without page reload.
- **SC-002**: 100% of movie cards render an IMDb score badge or standardized unrated placeholder with zero layout shift.
- **SC-003**: 100% of movie search results with identifiable censorship metadata display a clear censorship badge.
- **SC-004**: Users can filter out unwanted content (e.g., all premium links or all censored movies) within 2 clicks from the search results view.
- **SC-005**: Applying filters preserves existing playback preview, download matrix expansion, and external source link functionalities without degradation.

## Assumptions

- Source access tiers (Free vs. Premium vs. Freemium) are determined by source configuration in the registry and can be updated when source policies change.
- Censorship metadata is extracted from upstream scraper page titles, tags, and quality labels where Iranian movie sites customarily specify "سانسور شده" / "بازبینی شده" / "نسخه کامل". When an upstream site provides no indicator, status defaults to `unspecified`.
- IMDb ratings are extracted directly from the upstream source HTML metadata and schemas; no external third-party API keys or external rate-limited lookups are required.
- Filter controls conform to the application's existing dark-mode cyberpunk/minimalist aesthetic and RTL layout conventions.
