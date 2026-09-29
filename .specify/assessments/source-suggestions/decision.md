# Decision: User Source Suggestion Form

- **Slug**: source-suggestions
- **Decided**: 2026-09-29
- **Verdict**: go
- **Artifacts reviewed**: intake.md | research.md | problem.md | concept.md

## Scorecard

| Criterion | Rating | Justification |
|-----------|--------|---------------|
| Problem validity | strong | Real coverage gap; users discover new media hubs and domain migrations without a low-friction channel to report them. |
| Evidence strength | adequate | Grounded in current scraper structure (`apps/api/sources/`), UI source bar (`SourceStatusBar.tsx`), and direct user clarifications. |
| Value vs. inaction | strong | Unlocks crowdsourced source discovery and early warning on broken/migrated domains without adding external friction. |
| Feasibility / appetite | strong | Option A fits natively into existing stdlib SQLite `index.db` and Next.js frontend with small appetite (2–3 days). |
| Strategic fit | strong | Direct alignment with core mission of aggregating Persian media downloads while adhering to minimal-dependency architecture. |
| Risk posture | strong | Spam and flood risks effectively mitigated by 10/day IP rate limits and duplicate upvoting aggregation. |

## Verdict & Rationale

**Verdict: GO.**
The assessment proves clear user and maintainer value with zero external dependencies and low implementation complexity. Clarified constraints (Option A: minimal modal, SQLite table, 10/day IP rate limit, duplicate upvote counter, protected admin endpoint) fit the existing codebase cleanly and keep technical debt minimal.

## If go — Handoff to `/speckit-specify`

- **Problem**: Users lack an in-app channel to submit media source suggestions and domain updates, causing scraper coverage to lag behind real-world availability.
- **Chosen approach**: Option A — Minimal in-app modal form in `apps/web` connected to `POST /api/sources/suggest`, backed by a SQLite `source_suggestions` table in `apps/api/data/index.db`, 10/day per IP rate limiting, duplicate request counting, and a protected `GET /api/admin/suggestions` endpoint.
- **In scope**:
  - Web UI: Suggestion modal accessible from `SourceStatusBar` or header with fields: Target URL (required), Category (required), Source Name (optional), Sample Link (optional), Notes (optional).
  - API: `POST /api/sources/suggest` validating input, checking IP rate limit, and inserting or incrementing `request_count` on duplicate domains.
  - Admin: `GET /api/admin/suggestions` secured by `X-Admin-Token` to list suggestions by status and vote count.
  - Storage: `source_suggestions` table in SQLite schema with timestamps and review status (`pending`, `reviewed`, `implemented`, `rejected`).
- **Out of scope**:
  - Graphical web admin UI/dashboard.
  - User authentication or accounts for submitters.
  - Public voting or status boards.
  - Automated external notifications (webhooks, email).
  - Automated crawling/scraping of submitted URLs.
- **Success metrics**:
  - Over 5 valid unique domain suggestions received per month.
  - 100% of duplicate submissions aggregated into request counters without DB row bloat.
  - Zero external tool dependencies added to the repository.
- **Carried-forward open questions**: None.
