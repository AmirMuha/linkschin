# Feature Specification: Movie Source Expansion (20 Requested Sites)

**Feature Branch**: `005-movie-source-expansion`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "I need these 20 movies website be supported — Filimo, Namava, Filmnet, Gapfilm, Telewebion, Aparat, IMVBox, Danfilo, FilmChiin, FilmTarin, BabakFilm, Nda Media, Sarvnema, Salam Cinema, Tiwall, UpTV, Namasha, Rubika, Digitoon, Fam."

## Clarifications

### Session 2026-09-30

- Q: Where should the subscription streaming sites appear — a separate Streaming tab, or mixed into Movies marked "watch instead of download"? → A: No new tab. All twenty live in Movies; subscription entries render as watch destinations with no download. Streaming becomes a toggle inside the Movies tab.
- Q: Should a source that has gone dark stay listed permanently, or be hidden until someone brings it back? → A: Keep the entry, shown greyed out with its reason and the date it was last reachable. Visible in the list, excluded from search, and it resumes automatically once the domain returns.
- Q: How does a maintainer describe a new site that matches a standard pattern without custom code? → A: A hand-written configuration file read at startup, matching how base addresses are already changed today. No new admin screen.
- Q: Should a source with a dead main domain automatically retry a known alternate address? → A: Each source carries a primary address plus known fallback addresses tried in order. A dead primary is skipped and the next is used, with the reason surfaced.
- Q: If some of the twenty sites never offer public download links, is the feature delivered once all twenty are registered and honestly labelled, or does a minimum number need to work? → A: Success is a target for genuinely available sites, with every one of the twenty registered and honestly labelled either way. A site that cannot provide public links counts as correctly handled, not as a failure.
- Q: Live fingerprinting showed only 3 of 16 reachable sites run WordPress and `?s=` search is a soft-404 on at least two, so a general declarative "standard site pattern" engine is not justified. Narrow FR-022 to a declarative site profile plus per-site parsers, or keep the general engine? → A: Narrow FR-022. A new site is registered by configuration when a parser for its shape already exists; an unsupported shape gets a dedicated parser. This was applied as a default after the plan phase, without a separate answer from the user.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Finding a Requested Site in Search Results (Priority: P1)

A consumer searches for a Persian film or series title and expects the sites they already know and trust to appear among the results alongside the sources that work today. Every one of the twenty requested sites must be a known, discoverable source in the system — either contributing search results, or explicitly listed as available.

**Why this priority**: This is the entire ask. If a requested site is neither searchable nor visible anywhere, nothing else in this feature matters.

**Independent Test**: Search for a well-known Persian film title and verify that results are attributed to requested sites, and that every one of the twenty sites appears in the source listing surface.

**Acceptance Scenarios**:

1. **Given** a search for a popular Persian film title, **When** results are returned, **Then** results are attributed to their originating site by name, and the sites contributing those results are drawn from the requested list.
2. **Given** a consumer browsing available sources, **When** they view the source listing, **Then** all twenty requested sites are present, each showing whether it currently provides results and why if it does not.
3. **Given** a site that is present but not currently returning results, **When** the consumer views its entry, **Then** a plain-language reason is shown (for example: subscription service, unreachable, or not yet providing direct links) rather than the site simply being absent.

---

### User Story 2 - Watching Where a Title Is Available When No Download Exists (Priority: P2)

A consumer searching for a film discovers that some requested sites are subscription streaming services rather than direct-download providers. Rather than showing nothing or pretending a download exists, the consumer sees where each title can be watched legitimately, and the interface clearly separates "download" from "watch here".

**Why this priority**: A large share of the requested list is subscription or regional-availability services. Silently returning zero download links for them would look like a broken feature; surfacing watch destinations turns those entries into genuine value without ever crossing into bypassing a paywall.

**Independent Test**: Search for a title that exists only on a subscription service and verify the result shows a watch destination with no download button, and that the download and watch areas are visually distinct.

**Acceptance Scenarios**:

1. **Given** a subscription-based requested site, **When** a consumer searches for a title available there, **Then** the result shows a watch destination and no download link.
2. **Given** results that mix downloadable sources and subscription sources, **When** they are displayed together, **Then** downloadable entries show download actions and subscription entries show watch actions, and the two kinds are not confused for one another.
3. **Given** a consumer clicks a watch destination, **When** the destination opens, **Then** it leads to the site's own legitimate page or sign-up flow, and the platform does not proxy, mirror, or unlock any content.

---

### User Story 3 - Recovering When a Source Goes Down or Changes (Priority: P3)

Site domains in this region change frequently. A consumer should never be shown a broken result, and the maintainer should be able to point a source at a new address without a code change or redeploy.

**Why this priority**: Twenty new sources multiply the surface for domain churn. Without isolation and recovery, a single dead source degrades or breaks search for everyone.

**Independent Test**: Simulate a requested source returning errors or timing out and verify search still succeeds using the remaining sources, and verify the failing source is reported as degraded rather than silently dropped.

**Acceptance Scenarios**:

1. **Given** one or more sources are unreachable, slow, or returning unusable content, **When** a search runs, **Then** the search still completes and returns results from the healthy sources.
2. **Given** a source whose domain has changed, **When** a maintainer supplies the new address, **Then** the source operates on the new address without any change to shipped application logic.
3. **Given** a source that has stopped operating entirely, **When** it is disabled, **Then** it stops affecting search results immediately and its history and notes remain visible to maintainers.
4. **Given** any source returning an ad-shortener or parked-domain page, **When** results are produced, **Then** those results are discarded and never shown to the consumer.

---

### User Story 4 - Adding a Future Site Without Engineering Work (Priority: P4)

A maintainer identifies another film site worth adding. The site's behavior is described declaratively, and the platform gains a working source without writing new scraping code.

**Why this priority**: The twenty sites are a starting set, not a fixed list. This story ensures the feature scales to the next twenty without repeating twenty times the same engineering effort.

**Independent Test**: Describe an unconfigured site declaratively, enable it, and verify it participates in search using the same result and action model as the others.

**Acceptance Scenarios**:

1. **Given** a site that fits a known standard site pattern, **When** a maintainer describes it declaratively and enables it, **Then** it participates in search with no new scraping code written.
2. **Given** a site that does not fit any known pattern, **When** a maintainer attempts to add it declaratively, **Then** the platform reports what is missing rather than silently returning no results.
3. **Given** an added site behaves differently from every known pattern, **When** a dedicated handler is written for it, **Then** the dedicated handler is the only new code required, and shared behavior is unaffected.

---

### Edge Cases

- A requested site resolves but serves a bot-protection challenge, so a plain request returns no usable content. Result: the site is reported as requiring interactive access, not as broken, and never blocks the overall search.
- A requested site is reachable at a different top-level domain than commonly known (for example a `.ir` domain rather than a `.com` one). Result: the known-good address is recorded, and the failing one does not cause repeated failed attempts.
- A requested site redirects indefinitely or serves a challenge loop. Result: redirects are bounded, the source is marked degraded, and search continues.
- A single title returns a very large number of duplicate entries from one site. Result: duplicates for the same title from the same site are collapsed.
- A site's markup changes so titles stop parsing, but the site still returns valid pages. Result: the site is flagged as degraded for a maintainer, rather than silently contributing empty results forever.
- A source is mid-scrape when its domain dies. Result: the in-flight request is abandoned, and the request-level time budget still holds.
- A user searches for a title available on both a downloadable site and a subscription site. Result: both are shown, each labelled with the kind of action available.
- A requested site turns out to be a duplicate or alias of another site already supported. Result: it is registered as an alias and does not create a duplicate result stream.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST register every one of the twenty requested sites as a known source: Filimo, Namava, Filmnet, Gapfilm, Telewebion, Aparat, IMVBox, Danfilo, FilmChiin, FilmTarin, BabakFilm, Nda Media, Sarvnema, Salam Cinema, Tiwall, UpTV, Namasha, Rubika, Digitoon, and Fam.
- **FR-002**: System MUST NOT require a separate registration step for a requested site that is already supported under a different name; such a site MUST resolve to the existing entry.
- **FR-003**: System MUST distinguish sources that provide public, unauthenticated direct download links from sources that are subscription or regional-availability streaming services.
- **FR-004**: System MUST NOT add a separate Streaming category or tab. All twenty requested sites are searched under the existing Movies/Series category.
- **FR-005**: System MUST provide, within the Movies/Series category, a user-facing control that switches between showing only sources with direct download links and showing all sources including watch-only subscription entries. The default state MUST be downloads-only, so that existing users see no change in result volume until they opt in.
- **FR-006**: For a subscription or streaming source, the system MUST return the title, a watch destination pointing at the site's own page, and MUST NOT return any download link.
- **FR-007**: System MUST NOT circumvent, bypass, or defeat any paywall, membership check, region lock, DRM, or account requirement of an upstream site.
- **FR-008**: System MUST classify each requested source's operational state as one of: providing results, subscription-only, unreachable, requires interactive sign-in, or not yet provided, and MUST surface that state in the source listing.
- **FR-009**: System MUST surface a plain-language reason for any source not currently providing results.
- **FR-009a**: System MUST retain every registered source in the source listing even when it is not currently providing results, rendered as visibly inactive rather than removed, so that a requested site never silently disappears.
- **FR-009b**: System MUST show, for a source that is not currently providing results, the date it was last reachable or last known to work.
- **FR-009c**: System MUST automatically return a previously inactive source to active participation once it produces results again, without any manual intervention.
- **FR-010**: System MUST isolate each source such that an error, timeout, or malformed response from one source never prevents other sources from returning results for the same search.
- **FR-011**: System MUST enforce the existing per-source time budget of 7 seconds and the per-search budget of 10 seconds, and MUST return available results even when the overall budget is exhausted.
- **FR-012**: System MUST support externally configured base addresses per source so a domain change is applied through configuration alone, without application code changes. Each source MUST support an ordered list of addresses, comprising a primary address followed by any known fallback addresses.
- **FR-012a**: When a source's primary address is unreachable, the system MUST attempt the next configured address in order without maintainer intervention, and MUST report which address ultimately served the request.
- **FR-012b**: System MUST stop attempting an address that has been repeatedly unreachable and MUST NOT consume the per-source time budget retrying every address on every request.
- **FR-013**: System MUST support enabling and disabling a source through configuration, taking effect on the next startup without any change to application code.
- **FR-014**: System MUST validate any externally supplied base address as a well-formed absolute web address before use, and MUST reject invalid values rather than attempting a request.
- **FR-015**: System MUST follow up to a bounded number of redirects when contacting a source, and MUST mark a source that redirects in a loop as degraded rather than retrying indefinitely.
- **FR-016**: System MUST discard results originating from known advertising shorteners, referral redirects, and parked or for-sale domain pages.
- **FR-017**: System MUST present download and watch actions as visually distinct, so a consumer is never led to expect a download where only a watch destination exists.
- **FR-018**: System MUST collapse duplicate entries that represent the same title from the same source.
- **FR-019**: System MUST detect when a source's pages return successfully but no longer yield parseable results, and MUST flag it as degraded for maintainer attention.
- **FR-020**: System MUST provide a diagnostic view listing each source's current state, last successful activity, and last failure reason, for maintainer use.
- **FR-021**: System MUST allow a maintainer to mark a source as a duplicate or alias of another source, so that it does not produce a separate stream of results.
- **FR-022**: System MUST allow a new site to be registered by declarative configuration alone — its addresses, category, download-capability flag, and the name of a parser that already handles a site of its shape — without writing new scraping code. A site whose shape is not already supported requires a dedicated parser, and only that parser is new code; shared behaviour is unaffected. The configuration MUST be a hand-written file read at startup, consistent with how source base addresses are already supplied; this feature MUST NOT introduce a new administrative screen for adding sources.
- **FR-023**: When a declarative addition does not match any known pattern, system MUST report specifically what information is missing rather than registering a source that silently returns nothing.
- **FR-024**: System MUST preserve the existing behaviour of already-supported sources; adding the twenty requested sites MUST NOT reduce or alter results from sources that work today.
- **FR-025**: System MUST verify every new source offline against stored page samples, so that the test suite does not depend on any upstream site being reachable.
- **FR-026**: System MUST NOT store, host, proxy, or relay any media payload, for any source in this feature or any other.
- **FR-027**: System MUST apply the same Persian and Arabic text normalization to search queries issued against every newly added source as is applied to existing sources.

### Key Entities

- **Source**: A known upstream site, carrying a name, content domain, operational state, current base address, enablement status, and a record of its relationship to any duplicate or alias.
- **SourceOperationalState**: The current condition of a source — providing results, subscription-only, unreachable, requires interactive sign-in, or not yet provided — together with a plain-language reason and the time of the last success and last failure.
- **SourcePattern**: A declarative description of a recognized standard site shape, sufficient to configure a new source without custom code, including the addressing scheme, how to list results, and how to recognize a result page.
- **MediaItem**: A discovered title, carrying Persian and English names, category, year, artwork, and its originating source. An item from a subscription source carries a watch destination instead of download links.
- **WatchDestination**: A pointer to where a title may legitimately be watched, consisting of the destination address, the source name, and whether a subscription or account is required.
- **MovieDownloadVariant**: A downloadable file variant for a title, carrying resolution, codec, audio track, size, and the direct download address — present only for sources that provide public links.
- **SourceDiagnostic**: A maintainer-facing record of a source's recent behaviour, used to tell a working source from a silently broken one.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All twenty requested sites appear in the source listing for consumers and for maintainers, with zero sites absent, and a site that stops working remains listed rather than disappearing.
- **SC-001a**: A source that regains reachability is returned to active search participation with no manual action, verified by restoring a previously failing source and observing results again.
- **SC-002**: A consumer can run any one search and receive results attributed to at least five distinct requested sites, or an explicit per-site state explaining why a site did not contribute. The five is a target for sites that genuinely offer public links; a site that cannot offer one is correctly handled by being labelled, and is not counted as a failure.
- **SC-003**: Adding a site that matches a known standard pattern requires no new scraping code and reaches a working state within one configuration change.
- **SC-004**: With at least half of all registered sources failing, timeouting, or returning unusable content, a search still completes and returns results from the remaining healthy sources.
- **SC-005**: Zero search requests exceed the existing time budget, measured across the full registered source set.
- **SC-006**: Zero results are returned to consumers from advertising shortener, referral, or parked-domain pages.
- **SC-007**: Zero download links are surfaced for any subscription-gated, account-gated, or region-restricted title.
- **SC-008**: Zero media payloads pass through the platform's own network interface, measured by inspecting outbound traffic for the new sources.
- **SC-009**: A domain change for any newly added source is applied through configuration alone, with no change to shipped application logic and no redeploy.
- **SC-009a**: A source whose primary address is dead but which has a working fallback still returns results, verified by making the primary address fail and observing results from the fallback.
- **SC-010**: 100% of newly added sources are verifiable offline from stored page samples, with the full test suite passing with no network access.
- **SC-011**: A maintainer can determine the state and last failure reason of every source within one view, without inspecting logs.
- **SC-012**: Results from the pre-existing working sources are unchanged by this feature, verified by comparing result sets before and after for a fixed set of queries.

## Assumptions

- Sites were requested by name, not verified for current operation, currency, or whether they offer downloads. This spec registers all twenty regardless, and records each site's observed state rather than assuming any of them work.
- UpTV is already supported in the system; it remains in the twenty and is not duplicated.
- Several requested sites are subscription or regional-availability streaming services rather than direct-download providers. They are represented honestly as watch destinations, consistent with the project's prohibition on bypassing paywalls and the prohibition on relaying media.
- Aparat, Rubika, Digitoon, Fam, and Nda Media are video platforms, children's channels, or general media outlets rather than film portals. Per the user's direction they are all treated as part of the Movies/Series content domain for discovery.
- The reachable address for a site may differ from the commonly known one; the observed working address is recorded as the default and the alternate remains a configuration fallback.
- No source may require interactive sign-in to be usable; sites that do are recorded as requiring interactive sign-in and are not scraped.
- Site owners' terms are respected: only publicly available, unauthenticated links are extracted, and no paywall, membership, region lock, or account requirement is circumvented.
- Each source is a standalone module that depends on no other source, and shares only common parsing helpers, per the project's existing module-isolation principle.
- The result and action model (a title with its download variants or its watch destination) stays as it is today; only the set of sources feeding it grows.
- Adding twenty sources increases per-search load. Existing concurrency and caching behaviour is retained; a full per-source timeout sweep is the backstop when the overall budget is exhausted.
