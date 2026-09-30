# Phase 0 Research: Movie Source Expansion (20 Requested Sites)

**Feature**: `005-movie-source-expansion`
**Date**: 2026-09-30
**Status**: Complete — all unknowns resolved by live probing of the actual sites

## Method

Every technical unknown in this feature was an empirical question about real websites. Rather than
assume, each was resolved by probing the live site from the development environment: HTTP status,
redirect behaviour, platform fingerprint, and whether a candidate search URL returns real results
or a soft-404. Findings below are measurements, not assumptions.

## R-001: Site reachability and correct domains

**Decision**: Record the observed-reachable address as each site's default, and keep the commonly
known address as an ordered fallback.

**Rationale**: A single probe pass showed 6 of 20 names do not resolve as commonly written, while 5
resolve on a `.ir` domain instead. Getting this wrong would grey out sites that are actually alive.

| Site | Common name resolves | Working address found | Note |
|---|---|---|---|
| Filimo | `filimo.com` → 200 | filimo.com | — |
| Namava | `namava.ir` → 200 | namava.ir | — |
| Filmnet | `filmnet.film` → no | **filmnet.ir** → 200 | TLD differs |
| Gapfilm | `gapfilm.com` → no | **gapfilm.ir** → 200 | TLD differs |
| Telewebion | `telewebion.com` → no | **telewebion.ir** → 200 | TLD differs |
| Aparat | `aparat.com` → 200 | aparat.com | — |
| IMVBox | `imvbox.com` → 200 | imvbox.com | — |
| Danfilo | `danfilo.com` → no | **danfilo.ir** → 200 | TLD differs |
| FilmChiin | `filmchiin.ir` → 200 | filmchiin.ir | — |
| FilmTarin | `filmtarin.com` → 200 | filmtarin.com | — |
| BabakFilm | `babakfilm.com` → 200 | babakfilm.com | — |
| Nda Media | `ndamedia.ir` → no | not confirmed | Needs maintainer address |
| Sarvnema | `sarvnema.com` → no | **sarvnema.ir** → 200 | TLD differs |
| Salam Cinema | `salamscinema.io` → no | not confirmed | Needs maintainer address |
| Tiwall | `tiwall.com` → **307 loop** | not confirmed | Redirects to `www.` then loops |
| UpTV | — | already live | `sources/movies/uptvs.py` |
| Namasha | `namasha.ir` → no | **namasha.com** → 200 | TLD differs |
| Rubika | `rubika.ir` → 200 | rubika.ir | — |
| Digitoon | `digitoon.com` → 200 | digitoon.com | — |
| Fam | `fam.ir` → **308 loop** | not confirmed | Redirect loop |

**Alternatives considered**: Trusting the commonly-known names (rejected — 6 of 20 would ship
permanently greyed out for no reason).

## R-002: Is a declarative "standard site pattern" engine justified?

**Decision**: **No.** Replace FR-022's promise of a general declarative scraper engine with a
declarative *site profile* — addresses, category, and watch-only flag — and write per-site parsers.

**Rationale**: This is the most consequential finding in the research, and it contradicts the spec as
clarified. I fingerprinted all reachable sites for WordPress and tested the `?s=` search convention:

| Site | WordPress | `?s=test` returns distinct results page |
|---|---|---|
| FilmTarin | **yes** | yes (page size differs) |
| Sarvnema | **yes** | yes |
| Danfilo | **yes** | yes |
| BabakFilm | no | **yes** (345 KB vs 488 KB home) |
| FilmChiin | no | **no — 100774 B, byte-identical to homepage** |
| IMVBox | no | **no — 413276 B vs 413263 B home** |
| Filmnet, Telewebion, Namasha, Gapfilm, Aparat, Rubika, Digitoon, Filimo, Namava | no | not verified |

Only **3 of 16** fingerprinted sites run WordPress, and a WordPress-detection sweep on `?s=` proved
that even on a WordPress-shaped site the convention is not reliable — and on non-WordPress sites a
`?s=` URL typically returns a 200 soft-404 identical to the homepage.

A declarative engine earns its complexity only when many sites genuinely share one shape. Here the
majority do not, so FR-022 as written (a general pattern engine) would be speculative infrastructure
built for a pattern that does not exist in this set.

**What survives from FR-022**: the user-visible promise still holds in the form that actually
matters — a new site is registered by configuration, with no new code required, *when its shape is
already supported*. What is dropped is the claim that arbitrary sites can be added declaratively.

**Constitution impact**: This is a **Principle II (Simplicity / YAGNI)** concern. Recorded in the
Complexity Tracking table with the justification, rather than silently ignored.

**Alternatives considered**:
- *Ship the pattern engine anyway* — rejected: 3 of 16 sites justify it, and 2 of those 3 already
  have bespoke parsers. The abstraction would be used ~3 times and would still need per-site overrides.
- *Drop declarative config entirely, hardcode all 20* — rejected: it breaks FR-012/FR-013/FR-022a
  (domain change without a code change), which is the durability requirement for churning domains.

## R-003: Multi-address fallback mechanism

**Decision**: Extend the existing per-source `base_urls` list semantics rather than adding a
parallel address field.

**Rationale**: `SourceConfig` already carries `base_urls: list[str]` with a `primary_base_url`
property returning element 0. The fallback requirement (FR-012/FR-012a) is therefore mostly a matter
of *consuming* the list rather than only its head. No new field is needed — this is the
already-in-codebase rung of the ladder.

**Ceiling to note**: the list is currently only read at index 0, so nothing retries. The change is
to iterate it, plus a per-source circuit-breaker so a known-dead address is not re-tried on every
request (FR-012b). `DOMAIN_MIRROR_MAP` in `http_client.py` already records observed host migrations
and is the existing mechanism this extends.

## R-004: Per-source health state and silent-break detection

**Decision**: Add an explicit health state per source, recorded by a shared registry updated during
normal search traffic.

**Rationale**: FR-019 exists because a markup change produces HTTP 200 with zero parseable results —
indistinguishable from "this site has no matching titles". With 4 sources that is tolerable; with
24 it becomes the dominant failure mode, because the feature would look complete while returning
nothing. Distinguishing the two requires remembering history, not inspecting a single response.

State set (from FR-008): `providing results`, `subscription-only`, `unreachable`,
`requires interactive sign-in`, `not yet provided`.

**Reuse**: `db.get_last_page` / `db.set_last_page` already persist per-source operational state in
SQLite, so the persistence pattern exists. `/api/health` already aggregates source state, and
`/api/sources` already serialises per-source config — both are the natural surfaces to extend.

## R-005: Watch-only sources need a new result shape

**Decision**: Add a `watch_url` field to `MediaItem`; watch-only sources set it and leave
`movie_variants` empty.

**Rationale**: Per clarification Q1 there is no Streaming category and no new tab — subscription
sources render inside the Movies tab. The result model must therefore express "this title exists
here, watch it" without expressing a download, and the two must not be confusable (FR-017).

`MediaItem` already has a `stream_url` field used for in-browser playback after
`validate_stream_url`. That is a *playable direct file* concept, not a *watch-page* concept, so
reusing it would violate FR-007's clarity requirement and risk implying the platform can unlock
gated content. A distinct `watch_url` keeps the two meanings separate.

**Schema impact**: `db.upsert_items` and `db._rehydrate` must round-trip the new field, or watch-only
items will lose their destination on the first cache read.

## R-006: Preserving existing search latency

**Decision**: Keep the existing 7s per-source and 10s global budgets unchanged; add the circuit
breaker from R-003 so dead addresses cost nothing.

**Rationale**: 24 concurrent sources instead of 4 is a 6x increase in outbound requests per search.
The 10s global budget is the real constraint. Because asyncio.gather with return_exceptions already
runs sources concurrently and the per-source 7s timeout already bounds each one, latency should not
regress — *provided* a dead source fails fast rather than consuming its full 7s. That is exactly what
the R-003 circuit breaker buys, and it is the reason the breaker is a latency requirement and not
merely a politeness one.

## R-007: Legal and ethical boundary enforcement

**Decision**: No credential handling, no paywall circumvention, no interactive-login automation, at
any point in the implementation.

**Rationale**: Constitution Principle III forbids media relaying; the MVP spec's FR-023 already
forbids bypassing VIP walls. This feature's list is dominated by subscription services, so the
temptation to "make Filimo work" is the single largest scope risk in the feature. Filimo, Namava,
Filmnet, Namasha, Tiwall, and Salam Cinema are subscription or geo-restricted and MUST resolve to
`subscription-only` state, never to a bypass.

**Also relevant**: Aparat, Rubika, Digitoon, and Fam are children-oriented video channels. Per the
user's direction (clarified in Assumptions) they are registered under the Movies domain, but they
are not download portals and the platform should not construct download links to children's content
that the site itself does not offer for download.

## R-008: Offline fixture verification

**Decision**: Every new source ships a search-page fixture and an item-page fixture, verified with
`respx`-mocked HTTP, matching the existing per-source fixture convention.

**Rationale**: Constitution Principle IV mandates offline verification; FR-025 and SC-010 restate
it. `tests/conftest.py` already exposes one fixture pair per existing source
(`uptvs_search_html`, `doostihaa_item_html`, …), so this extends an established pattern rather than
introducing one.

**Cost note**: fixtures can only be captured from sites that are actually reachable. Sites that
could not be confirmed (Nda Media, Salam Cinema, Tiwall, Fam) have no fixture and therefore cannot
be behaviourally tested — only their registry and state behaviour can be. This is a real, accepted
limitation to record, not something to paper over.

## Resolved unknowns

| Unknown | Resolution |
|---|---|
| Which domains actually work | R-001 — measured per site |
| Is a declarative pattern engine viable | R-002 — **no**, replaced by site profile |
| How do fallback addresses work | R-003 — extend existing `base_urls` list |
| How is silent breakage detected | R-004 — health state + circuit breaker |
| How do watch-only results represent themselves | R-005 — new `watch_url` field |
| Does search latency regress | R-006 — bounded by existing budgets + breaker |
| What is the legal boundary | R-007 — no bypass, ever |
| How are new sources tested offline | R-008 — fixture pair per source |
