# Contract: Source Kind, Status, and Filter UI

**Feature**: [006-music-sources-expansion](../spec.md) | **Date**: 2026-09-30
**Status**: Modified — extends two existing frontends

This codebase ships **two** frontends. Both consume the same API contracts, and both must be updated. The Jinja side serves `apps/api/web/templates/`; the Next.js side serves `apps/web/src/`.

## Components touched

| File | Change |
|---|---|
| `apps/api/web/templates/_music_card.html` | Render a link-out card for reference items; no `<audio>` element |
| `apps/api/web/templates/base.html` | Show kind and inactive reason in the source list |
| `apps/web/src/components/SourceStatusBar.tsx` | Kind badge, status, and reason per source |
| `apps/web/src/components/InViewFilterBar.tsx` | Per-source hide toggles, persisted to local storage |
| `apps/web/src/types/media.ts` | `SourceStatus` gains the four new fields |
| `apps/web/src/lib/api.ts` | Send the saved hidden set as repeated `sources` params |

## Result card

### Full source

Unchanged from today: the card shows cover art, title, artist, an `<audio>` player, and one control per download variant. The existing `_music_card.html` already does this.

### Reference source

A reference result MUST render as a link-out card:

| Element | Requirement |
|---|---|
| Title, artist, cover art | Shown as available |
| Outbound link to `page_url` | Present, opens in a new tab, `rel="noopener"` |
| Audio player | **Must not be rendered** |
| Download controls | **Must not be rendered** |
| Kind marker | A visible label that the result links out to the site |

A player or download control rendered for a reference item is a contract violation (SC-003), because it is a control that provably cannot work. Hiding it via CSS while leaving it in the DOM does not satisfy this — the element must be absent.

**ponytail: no CSS-hiding fallback.** Rendering then hiding the player would still ship a broken control to assistive technology and to any client that ignores the stylesheet. Absence is the correct implementation and is also the smaller one.

The existing "no direct download link found" message in `_music_card.html` is the current rendering for a media-less item. It is reused, but its wording changes: it currently reads as a failure, and for a reference source it must read as a deliberate link-out.

## Source list entry

Each source shows:

| Field | Display rule |
|---|---|
| Name | Always |
| Kind | Badge, always. Full and reference must be visually distinguishable |
| Status | `active` \| `degraded` \| `inactive` — always visible |
| Reason | Required whenever status is not `active`; names the actual cause |

Reason text must name the real cause — a dead domain, a changed domain, an account requirement, a licensed service, a video platform, or gated access. A generic "unavailable" is non-conforming (G3 in the sources contract).

## Per-user hide filter

| Rule | Detail |
|---|---|
| Placement | Alongside the existing source filter bar, not a new page |
| Persistence | `localStorage` on the client; no account, no server state (FR-029) |
| Scope | Affects only the user who set it; never the default enabled set (FR-030) |
| Visibility | A hidden source is still **listed** with its status, so the user can see what they turned off and restore it |
| Non-overridable | A source the system has marked `degraded` or `inactive` cannot be hidden away; its state is reported to every user regardless (FR-031) |
| Reset | A control to restore all sources to the default set |

The hidden set is sent on each search as repeated `sources` query parameters (see the search contract). It is never written into the shared cache.

## Accessibility

Non-negotiable, and cheap here:

- Kind and status information conveyed by text, not by colour alone.
- The outbound link has a discernible name; the icon-only variant requires an accessible label.
- Hide toggles are real form controls with labels, reachable and operable by keyboard.
- Focus order follows visual order in the filter bar.
- A `degraded` or `inactive` state is announced, not only coloured.

## Regression constraint

For `category=movies` and `category=games`, none of this UI changes (FR-028). Kind badges and hide toggles appear for music sources; movies and games render exactly as they do today.
