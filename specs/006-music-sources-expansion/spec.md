# Feature Specification: Music Source Expansion

**Feature Branch**: `006-music-sources-expansion`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "Here are 20 Iranian websites and platforms for listening to, streaming, and downloading music, including Persian songs, Iranian artists, playlists, and international music... I need these 20 music websites be supported." The 20 named sites are: Radio Javan, Musicdel, Nex1Music, Music-fa, UpSong, UpMusics, MusicTarin, Tehran Music, Shenoto, Melodify, TakMusics, 1RJ, FarsiChart, Aparat, Namasha, Rubika, Fam, SoundCloud, Spotify, YouTube Music.

## Scope Interpretation

The 20 named sites fall into two groups, distinguished by what the aggregator can honestly offer for each.

**Full sources (11)** — download portals that publish per-track audio file links on public pages. For these the platform resolves a playable stream and labelled download options.

Radio Javan, Musicdel, Nex1Music, Music-fa, UpSong, UpMusics, MusicTarin, Tehran Music, Melodify, TakMusics, 1RJ.

**Reference sources (9)** — sites where audio is behind an account, a paid subscription, a licensed third-party player, or a video upload. The platform does not attempt to extract or relay their media. It indexes their entries and sends the user to the site itself.

Shenoto, FarsiChart, Aparat, Namasha, Rubika, Fam, SoundCloud, Spotify, YouTube Music.

Reference sources are a supported source type, not a fallback. A user searching for a track finds these results alongside the full sources, clearly marked as links out rather than playable in place. This is what makes all 20 named sites genuinely supported: the 11 we can serve directly are served, and the other 9 are honestly reachable instead of being silently dropped or half-scraped.

This also keeps the project's No Media Relaying principle strictly intact — no reference source's media passes through the aggregator, and no user credentials are ever requested, stored, or forwarded.

### Clarification Resolutions

- **Video platforms**: the answer given was *C*, but the stated intent in the streaming-services answer was to list and link out with no in-app listening or downloading. Both video platforms and streaming services are therefore treated identically as reference sources. *(Interpretation flagged for confirmation — option C as originally offered described extracting a video's audio as a playable stream, which the stated intent rules out. If a video's audio should instead be playable in-app, that is a different outcome and this spec needs revisiting.)*
- **Credential-linked streaming services**: answered *list-only*. No credential-linked capability is built. See the reference sources above.
- **Lyrics**: answered *A*, audio only. Lyrics are out of scope.

## Clarifications

### Session 2026-09-30

- Q: When a search returns a mix of playable results and link-out results, in what order should they appear? → A: Full sources first, then reference sources, each group ranked by existing relevance
- Q: What should a user see when a music source has stopped working — is a single failed request enough to mark it, or does it take repeated failures? → C: Mark degraded when the source has failed across 3 separate searches, rather than 3 requests in a row
- Q: Should a user be able to hide a music source they don't want — for example turning off Aparat because they only want direct-download sites? → B: A per-user filter remembered in the browser, applied on top of the default enabled set
- Q: The spec now uses "kind" in some places and "tier" in others for the same full-versus-reference split — which word should be the standard one? → A: Use "kind" everywhere; "tier" is removed

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Finding a Persian song across many sources at once (Priority: P1)

A listener searches for a Persian song title. The aggregator queries every enabled music source in parallel and returns a merged, de-duplicated set of results. The user sees that the same track is available from several sites and can pick any of them without retyping the query.

**Why this priority**: This is the entire user-facing value of adding sources. More sources only help if they all participate in one search and the user can tell them apart.

**Independent Test**: Run a search for a well-known Persian track against the live stack and confirm results from multiple distinct music sources appear in a single response, each labelled with its originating site.

**Acceptance Scenarios**:

1. **Given** a search term matching a popular Persian track, **When** the user submits the search, **Then** results from at least six distinct music sources are returned together in one response, each showing which site it came from.
2. **Given** the same track exists on multiple sites, **When** results are displayed, **Then** each source's copy appears as its own result attributed to that source, and no entry is silently dropped for being a duplicate of another source's entry.
3. **Given** a user types Persian text using Arabic characters, Persian digits, or a mix of ZWNJ spacing variants, **When** the search is submitted, **Then** it is normalized before it reaches the sources so that equivalent spellings return the same results.
4. **Given** one music source is slow or unreachable, **When** the search completes, **Then** the user still receives results from every other source and is not shown an error for the failed one.
5. **Given** a track is available from both a full source and a reference source, **When** results are displayed, **Then** both appear, and the user can tell which can be played in place and which links out to the site.
6. **Given** a search returns both playable and link-out results, **When** results are displayed, **Then** every playable result appears above every link-out result, and the relative order within each group is unchanged by the presence of the other group.

---

### User Story 2 - Playing and downloading a track from a full source (Priority: P2)

A listener opens a result from a download portal, and the system resolves the track to playable audio and downloadable files at multiple quality levels. The listener can start playback in the browser without leaving the site, and can separately download the higher-quality file.

**Why this priority**: A source that lists tracks but yields no playable link adds noise without value. Every full source that ships enabled must reach this outcome.

**Independent Test**: Take a single result from one newly added full source, open it, and confirm a playable stream plus at least one downloadable file are presented.

**Acceptance Scenarios**:

1. **Given** a result from a full source, **When** the user opens it, **Then** the track is shown with a playable audio link and one or more downloadable files at labelled quality levels.
2. **Given** a source publishes several quality levels of the same track, **When** the track is opened, **Then** each distinct quality is offered separately rather than only the best one.
3. **Given** the user selects play, **When** playback starts, **Then** the audio streams from the upstream site directly to the user's device and is never routed through the aggregator's own server.
4. **Given** a full-source track page yields no usable audio link, **When** the user opens it, **Then** the system reports that the track is unavailable from that source instead of presenting a broken or non-functional player.

---

### User Story 3 - Reaching tracks the platform cannot play (Priority: P3)

A listener searches for a track that only exists on a subscription service or a video platform. The aggregator still surfaces it, clearly marked as a link out, and the user continues to the site to listen there.

**Why this priority**: This is what turns the 9 non-download sites from exclusions into supported sources. Without it, a third of the requested list is silently missing, and users searching for those tracks conclude the platform simply does not index them.

**Independent Test**: Search for a track present on a reference-only site and confirm it appears in results, is marked as a link out, and leads to the correct page on the originating site.

**Acceptance Scenarios**:

1. **Given** a track is listed on a reference source, **When** the user searches for it, **Then** the result appears in the merged result set, attributed to that source and clearly marked as linking out rather than playable in place.
2. **Given** a reference-source result, **When** the user activates it, **Then** the user is taken to the track's page on the originating site.
3. **Given** a reference source, **When** the user views its entry in the source list, **Then** the reason it is not playable in place is stated — that it requires an account, a subscription, a licensed player, or is a video platform.
4. **Given** a reference source, **When** the user views any result from it, **Then** no in-app player control and no download control are offered.
5. **Given** a user hides a source, **When** the user searches again on the same device, **Then** the hidden source's results are absent and the source is still listed with its status, so the user can see what they turned off and turn it back on.
6. **Given** a user has hidden a source, **When** a different user searches, **Then** that source's results are unaffected.

---

### User Story 4 - Every named site has a visible, honest status (Priority: P4)

A user or maintainer reviews the source list and can see, for every one of the 20 named sites, whether it is active, what kind of source it is, and — when it is not active — why not.

**Why this priority**: The user was given a specific list of 20 names. Delivering them with no account of which are playable and which are link-outs would leave the user unable to tell what they actually got. Recording the disposition of every name closes the loop.

**Independent Test**: Review the source list and confirm all 20 names appear, each with a kind and an active status, and each inactive entry carrying a specific stated reason.

**Acceptance Scenarios**:

1. **Given** the full list of 20 named sites, **When** the user reviews the source list, **Then** every name appears with its source kind and whether it is active, and inactive entries display a short specific reason.
2. **Given** a site whose domain has changed, expired, or been taken over, **When** it is checked, **Then** it is recorded as inactive with that reason, and it is excluded from search rather than returning empty or misleading results.
3. **Given** a site that was previously active but has begun failing, **When** the user views the source list, **Then** its degraded status is visible without the source being silently removed.
4. **Given** a site gated behind a captcha, interstitial, or login, **When** it is checked, **Then** it is recorded as blocked with that reason and is not partially scraped.
5. **Given** a source has failed on 1 or 2 searches, **When** the user views the source list, **Then** the source is still shown as active and is still queried, because a single outage is not evidence the source is gone.
6. **Given** a source has failed on 3 separate searches, **When** the user next loads the interface, **Then** the source is shown as degraded, is excluded from returning results, and states that a maintainer must restore it.

---

### User Story 5 - Verification without network access (Priority: P5)

A maintainer changes a source's parsing rules and needs confidence the change is correct before it goes live, without depending on any external site being reachable or unchanged.

**Why this priority**: The project constitution makes offline verification a hard requirement. Upstream sites change layout frequently; without offline checks, routine maintenance would break whenever a site is momentarily unreachable.

**Independent Test**: Run the full test suite with the network unavailable and confirm every music source still passes.

**Acceptance Scenarios**:

1. **Given** no network access, **When** the full test suite runs, **Then** every music source's tests pass, including the newly added ones.
2. **Given** a captured real response from each newly added full source, **When** its parsing is exercised, **Then** the expected titles, links, and quality variants are produced from the captured data.
3. **Given** a captured real response from each newly added reference source, **When** its parsing is exercised, **Then** the expected titles, page addresses, and cover art are produced, and no media link is emitted.
4. **Given** a source returns a domain-parking page, an advertisement, or an error instead of results, **When** parsing is attempted, **Then** the source yields no results rather than junk entries.
5. **Given** a source is slow to respond, **When** the time budget is exceeded, **Then** it is abandoned without blocking the overall search.

---

### Edge Cases

- **Domain change or takeover**: An Iranian portal rotates its domain and the old one becomes a parked or ad page. The source must be recognized as dead rather than parsed for whatever the parked page happens to contain.
- **Two names, one site**: Nex1Music and 1RJ are related properties. They must be treated as separate source entries so a single failure does not disable both, but must not produce confusingly duplicated labels in results.
- **A name already present**: Nex1Music is already supported under a different domain than the one supplied, and Radio Javan is already recorded as inactive. Adding the new names must reconcile with the existing entries rather than creating a second overlapping record.
- **Missing domain**: At least one name in the supplied list carries no domain at all. It must be researched during implementation, and recorded with a clear status if it cannot be confirmed.
- **Reference source that turns out to expose direct files**: A site classified as a reference source may be found to publish direct audio links. It is promoted to a full source, with the kind recorded per source rather than assumed from what sort of site it is.
- **Full source that turns out to be gated**: A download portal may be found to hide its links behind a captcha, an interstitial, or a login. It is demoted to inactive-with-reason, never partially scraped.
- **Persian/Arabic character drift**: Sites inconsistently use Arabic ي/ك versus Persian ی/ک, and Persian versus Arabic-Indic digits. Extraction must not break on either.
- **Non-HTTP links**: Download links are sometimes wrapped in redirect scripts or ad shorteners. Only genuine HTTP(S) media links may be presented, and only for full sources.
- **Very large or very small catalogs**: Some portals expose thousands of results per query with no pagination. A source must not stall the overall search because of catalog size.
- **Reference source with no Persian content for a Persian query**: A reference source indexed in a different script must not be treated as a failure; it simply may contribute no result to a given query.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support a registry of individually configurable music sources, each of which can be enabled or disabled independently of the others.
- **FR-002**: Each source MUST be classified as either a full source, which resolves to playable and downloadable media, or a reference source, which resolves only to a page address on the originating site.
- **FR-003**: The system MUST query all enabled music sources for a single user search and merge their results into one response.
- **FR-004**: Each returned result MUST be attributed to the specific source it came from, and results from different sources MUST remain distinguishable even when they represent the same track.
- **FR-005**: A result MUST be visibly marked with its source's kind, so the user can tell a playable result from a link-out before acting on it.
- **FR-005a**: Search results MUST be ordered with all full-source results before any reference-source results; within each group, results MUST retain the existing relevance ordering unchanged.
- **FR-006**: The system MUST normalize user search text — including Persian and Arabic character variants, Persian and Arabic-Indic digits, and ZWNJ spacing — before the text reaches any source.
- **FR-007**: A failing, slow, or unreachable source MUST NOT prevent results from the remaining sources from being returned to the user.
- **FR-008**: Each source MUST have an independently enforced time budget so that a slow source is abandoned without exceeding the overall search budget.
- **FR-009**: Opening a result from a full source MUST resolve the track to a playable audio link and to one or more downloadable files, each labelled with its quality level.
- **FR-010**: Where a full source publishes several quality levels of one track, each MUST be offered as a distinct download option.
- **FR-011**: A result from a reference source MUST resolve only to the track's page on the originating site, and MUST NOT offer an in-app player control or a download control.
- **FR-012**: A reference source MUST NOT be queried for, proxied, or granted access to any media asset, and MUST NOT cause the user to be asked for, or the system to store, any account credential or subscription token.
- **FR-013**: Media MUST be delivered to the user directly from the upstream host. The aggregator MUST NOT buffer, proxy, download, or relay any media payload.
- **FR-014**: The system MUST NOT present a download link that resolves to an advertisement, a referral redirect, or a non-audio resource.
- **FR-015**: A full-source result that yields no usable audio link MUST be reported as unavailable for that source rather than rendered as a broken player.
- **FR-016**: Search responses MUST preserve the project's existing result-shaping and ordering conventions so that adding sources does not alter the behaviour of the existing movies and games categories.
- **FR-017**: The system MUST display, for every registered source, its kind and whether it is active, and for every inactive source a short specific reason.
- **FR-018**: A source that is recognized as dead — domain parked, taken over, or persistently failing — MUST be excluded from returning results and MUST be marked with the reason.
- **FR-018a**: A source MUST be marked degraded only after it has failed across 3 separate user searches. A single failed request or a single failed search MUST NOT change a source's displayed status. Once degraded, a source MUST be excluded from returning results until a maintainer restores it.
- **FR-018b**: A source's degraded status MUST be derivable from observed failures alone, without a maintainer editing the registry, and MUST be visible in the interface on the next page load after the third failure.
- **FR-029**: The user MUST be able to hide any individual source from their own searches, and the choice MUST persist across page reloads for that user without requiring an account.
- **FR-030**: A user's hidden-source choice MUST affect only that user's searches. It MUST NOT change the default enabled set, other users' results, or the source registry.
- **FR-031**: A user's hidden-source choice MUST NOT be able to hide a source the system has already marked degraded, dead, or inactive-with-reason, since those states are reported to every user regardless.
- **FR-019**: Every newly added music source MUST be verifiable by automated checks that run to completion with no network access, using captured representative responses.
- **FR-020**: A source that returns a parked page, an advertisement, or an error page MUST yield zero results rather than junk entries.
- **FR-021**: The classification of a source MUST be determined by what that source actually exposes at build time, not assumed from the kind of site it is; a source's classification may be corrected after verification.
- **FR-022**: Where a site requires a user account, a paid subscription, or a licensed third-party player, the system MUST register it as a reference source and MUST NOT attempt to extract its media.
- **FR-023**: Where a site is a video platform rather than an audio source, the system MUST register it as a reference source and MUST NOT add a video variant to the media model.
- **FR-024**: Any site named in the input that already has a registry entry under a different domain MUST be reconciled with the existing entry, not duplicated.
- **FR-025**: A named site supplied without a domain MUST be researched during implementation and recorded with its confirmed domain or with the reason no domain could be confirmed.
- **FR-026**: Any source whose real content is gated behind a captcha, interstitial, or login MUST be recorded as blocked and MUST NOT be partially scraped.
- **FR-027**: Lyrics MUST NOT be captured, stored, or displayed by this feature.
- **FR-028**: Adding music sources MUST NOT change the behaviour, results, or performance of the existing movies, games, and already-supported music categories.

### Key Entities

- **Music Source**: An individually configured, independently enable-able upstream site that the aggregator queries for music. Attributes: identity, display name, the one or more domain addresses it is reachable at, its category, its kind (full or reference), whether it is active, the reason it is inactive if not, and its per-request time budget. One music source may exist at more than one domain; it is still a single source for availability purposes.

- **Music Track**: A single piece of music as presented to the listener. Attributes: display title, performing artist, cover art, the source it came from, the source's kind, and — for a full source — the playable link and the set of download options. For a reference source, a track carries the page address and no media. A track belongs to exactly one source; the same recording appearing on two sources is two tracks.

- **Download Variant**: One downloadable file for a track at a specific quality level. Attributes: the quality label, the file's direct address, and optionally the file size. A track has one or more variants. Reference sources produce no variants.

- **Source Disposition Note**: The recorded outcome for a named site that is registered but not producing results. Attributes: the site name, its domain if known, and the reason it is not active — for example dead or changed domain, or access gated by captcha, interstitial, or login.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A search for a well-known Persian track title returns results from at least six distinct music sources in a single response.
- **SC-002**: For a track available from a full source, the listener can begin playback within two interactions from the search results.
- **SC-003**: For a track found only on a reference source, the listener can reach the correct page on the originating site within two interactions, and is never shown a player or download control that cannot work.
- **SC-004**: 100% of the newly added music sources pass their automated checks with the network unavailable.
- **SC-005**: When any single music source fails, times out, or returns an error, the search still returns results from every other enabled music source.
- **SC-006**: A search across all enabled music sources returns its complete result set within 3 seconds when every source responds normally.
- **SC-007**: All 20 sites named in the request appear in the source list, each with a kind and an active status — zero sites omitted without explanation, and every inactive entry carrying a specific stated reason.
- **SC-008**: No media payload is transmitted through the aggregator under any circumstance, verifiable by observing that every media request originates from the user's client to the upstream host, and that no reference source is ever asked for credentials.
- **SC-009**: A source that fails across 3 separate searches is marked degraded and excluded from results on the next page load after the third failure; a source that has failed only once or twice is still shown as active.
- **SC-010**: Adding the new music sources causes no regression in the existing movies, games, and previously supported music search behaviour.

## Assumptions

- **Existing patterns are reused, not reinvented.** New sources are added as standalone plugins conforming to the existing source plugin contract, registered in the existing source registry, and verified with the existing offline fixture approach. No new source framework, no new persistence, no new caching layer.
- **The existing music track data model is sufficient.** No new media kind is added. A reference source's track is distinguished by the presence or absence of media fields, not by a new model.
- **Reference sources are a first-class source kind**, configured per source like any other, and not implemented as a special case in the search path.
- **Music sources only.** The media kind for this feature is audio; spoken-word, podcast, and audiobook catalogs are not included.
- **No credentials are stored, requested, or forwarded by the aggregator.** This is a hard consequence of the reference-only treatment of credentialed services, and is consistent with the No Media Relaying principle.
- **Legality of direct links is taken as given for the download portals.** Each portal is treated as publishing links it intends to be followed. The user is responsible for ensuring their own use complies with applicable law and with the rights of the artists and rights-holders.
- **Search result volume is bounded by source configuration.** A source returning an unbounded catalog is limited by the search's existing result budget rather than by source-specific pagination.
- **Domain changes are a recurring, expected condition.** Sources are expected to break over time; the registry's ability to record a source as disabled with a reason is the accepted handling, not continuous monitoring.
- **Upstream sites may be unreachable from the development environment at build time.** Where a live response cannot be captured, the source is still recorded with its status and kind, and verification is deferred until a capture is available — it is not dropped from the registry.
- **Test fixtures are captured real responses**, not hand-written approximations, so that parsing checks reflect genuine upstream markup.
- **The existing movies and games source behaviour is unchanged** by this feature.
- **No user accounts are introduced by this feature.** A user's hidden-source choice is the only per-user state, and it lives entirely in that user's own browser. It is not an account, it is not a profile, and it does not follow the user to another device.
- **Lyrics are not captured**, per Q3. Sites that publish lyrics are not treated as failing for omitting them.

## Dependencies

- The existing source plugin contract, shared URL-cleaning and parked-page detection helpers, and Persian digit normalization utilities.
- The existing source registry and its environment-variable override mechanism for domains and enable/disable state.
- The existing search request budget and per-source timeout conventions.
- The existing media data models for music tracks and download variants, which must express "no media, page link only" without a new media kind.
- The existing offline fixture and mocked-HTTP test approach.
- Live capture of representative responses from each supported portal, obtainable from an environment with access to Iranian sites, and for the international services from a normal network.

## Out of Scope

- Any capability to play, stream, or download media from a reference source. Reference sources are link-outs only.
- Any account-linked or subscription-linked capability for Spotify, YouTube Music, SoundCloud, or Shenoto.
- Audio extraction from video platforms. Aparat, Namasha, Rubika, and Fam are registered as reference sources; no video variant is added to the media model.
- Lyrics, in any form.
- Playlists, podcasts, and audiobooks as a media kind.
- FarsiChart as a link source for audio; it is registered as a reference source.
- Any change to how media is delivered, in line with the No Media Relaying principle.
- Automatic monitoring or alerting for source health beyond what the interface already displays.
