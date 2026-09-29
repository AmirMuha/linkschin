# Concept: User Source Suggestion Form

- **Slug**: source-suggestions
- **Created**: 2026-09-29
- **Recommended option**: Option A — Minimal In-App Modal with SQLite Intake & Protected API

## Options

### Option A — Minimal In-App Modal with SQLite Intake & Protected API
- **Sketch**: A lightweight modal dialog in `apps/web` accessible from `SourceStatusBar` or header. Form requires Target URL and Category, with optional Name, Sample Links, and Notes. Submissions post to `POST /api/sources/suggest`. Backend validates input, checks client IP against a 10/day rate limit, and checks the database: if the domain/URL already exists, increments `request_count`; otherwise inserts a new record with status `pending`. Maintainers query pending/triage submissions via `GET /api/admin/suggestions` protected by a secret token header (`X-Admin-Token`).
- **Appetite**: Small (2–3 days).
- **Trade-offs**:
  - *Wins*: Zero new external dependencies or services; reuses existing SQLite `index.db`; low friction for users; immediate feedback via toast.
  - *Sacrifices*: No graphical admin UI for triage (maintainers inspect via API/JSON or simple script).
  - *Risks*: In-memory IP tracking resets on process restart (mitigated by storing IP timestamp in SQLite).
- **Rabbit holes**: Over-complicating URL normalization across subdomains/paths; over-engineering admin auth beyond a static token.

### Option B — In-App Modal with Full Graphical Admin Management
- **Sketch**: Adds the submission modal from Option A plus a dedicated `/admin/suggestions` web dashboard with session-based login, status toggling (`pending` -> `investigating` -> `implemented` -> `rejected`), maintainer notes, and search/filtering.
- **Appetite**: Medium (1–2 weeks).
- **Trade-offs**:
  - *Wins*: Visual review workflow for non-technical maintainers.
  - *Sacrifices*: High complexity: introduces authentication middleware, login routes, admin state management, and UI maintenance for low-volume data.
- **Rabbit holes**: Building a custom auth and permission system for a single admin page.

### Option C — External Issue Template Redirect (No-Code Intake)
- **Sketch**: Replace the in-app submission form with a direct link in the UI to a pre-filled GitHub Issue template or external form (e.g. Google Forms / Tally).
- **Appetite**: Small (< 1 day).
- **Trade-offs**:
  - *Wins*: Zero code changes in API, zero DB storage, zero spam risk.
  - *Sacrifices*: Requires users to have a GitHub account or visit an external site; high friction leads to low submission volume from non-technical users.
- **Rabbit holes**: None.

## Recommendation

**Option A (Minimal In-App Modal with SQLite Intake & Protected API)** is strongly recommended.
It satisfies all core requirements and clarified constraints:
- Low-friction in-app submission with required/optional fields.
- Zero extra infrastructure (persists directly in existing SQLite database via stdlib).
- Built-in spam protection (10 submissions/day per IP).
- Automated deduplication with upvote counter.
- Avoids the unjustified complexity of a full admin dashboard (Option B) while avoiding the external drop-off of GitHub redirect (Option C).

## Out of Scope (for the recommended option)

- Graphical web admin UI or dedicated admin dashboard routes.
- Multi-user authentication, roles, or permissions.
- Public voting or public status boards.
- External webhook or email dispatch notifications.
- Automatic website scraping / validation of the suggested URL.

## Assumptions to Validate

- Maintainers are comfortable reviewing suggestions via `curl` / HTTP client or inspecting `index.db` directly.
- Standard IP detection (`request.client.host` or configured proxy headers) reliably reflects client identity in production deployment.
- Domain extraction cleanly captures apex domain for deduplication without false collisions.
