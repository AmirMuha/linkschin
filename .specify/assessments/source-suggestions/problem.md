# Problem Definition: User Source Suggestion Form

- **Slug**: source-suggestions
- **Created**: 2026-09-29
- **Inputs used**: intake.md, research.md, user input

## Problem Statement

Users of the media search platform discover valuable Persian media sources and domain changes that the platform does not currently index, but lack a direct, low-friction channel inside the application to report or request them. As a result, scraper expansion is bottlenecked solely on maintainer discovery and manual research.

## Affected Users & Stakeholders

- **Users**: Media consumers searching for movies, series, games, or music — currently face missing search results when content only lives on unindexed sources, with no in-app way to suggest them.
- **Maintainers / Developers**: System custodians and scraper authors — need high-signal, prioritized suggestions of real-world sources from active users to direct development effort effectively.

## Goals

- Provide a simple, accessible in-app submission form in the web UI for users to suggest media sources.
- Capture essential source metadata (site URL and media category required; name, sample URLs, and notes optional).
- Protect intake against spam and duplicate pollution using IP rate limits and request counter aggregation.
- Equip maintainers with a private, authenticated inspection interface to triage and prioritize high-demand sources.

## Non-Goals

- Automated scraper generation or AI-based source extraction (scrapers will continue to be manually implemented).
- Public suggestion tracking board or user upvote rankings (intake remains private to maintainers).
- In-app notification or user accounts for suggestion submission (intake is lightweight and anonymous).
- Automated external status alerts (email/SMS/webhooks out of scope for initial release).

## Success Metrics

- Active submission volume of valid new source suggestions (> 5 verified unique domains submitted per month).
- Reduction in unindexed source discovery friction (0 external GitHub issue requirements for casual users).
- Duplicate aggregation accuracy (100% of repeated submissions increment counter rather than creating duplicate rows).

## Cost of Inaction

The platform's content catalogue remains limited to existing scrapers; unindexed sources known to users remain unknown to maintainers; domain churn causes search coverage degradation.

## Open Questions

None. All core unknowns clarified during intake and research.
