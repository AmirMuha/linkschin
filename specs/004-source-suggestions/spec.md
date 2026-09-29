# Feature Specification: User Source Suggestion Form

**Feature Branch**: `004-source-suggestions`

**Created**: 2026-09-29

**Status**: Draft

**Input**: User description: "submittable form for allowing users to suggest and request for sources they know - Option A: Minimal in-app modal form in apps/web connected to POST /api/sources/suggest, backed by a SQLite source_suggestions table in apps/api/data/index.db, 10/day per IP rate limiting, duplicate request counting, and a protected GET /api/admin/suggestions endpoint."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Suggesting a New Source via In-App Form (Priority: P1)

A media consumer discovers a media website that the platform does not currently index. From the web interface, the user opens a lightweight suggestion dialog, fills in the website URL and selects its primary content category (Movies/Series, Games, or Music), adds optional context, and submits. The system accepts the submission and displays an immediate success confirmation.

**Why this priority**: Core value of the feature. Without the ability for users to submit a suggestion, no crowdsourced source discovery is possible.

**Independent Test**: Can be tested independently by opening the form, submitting a valid URL and category, and verifying that the submission is persisted and the success notification is displayed.

**Acceptance Scenarios**:

1. **Given** a user on any page of the web application, **When** they click "Suggest a Source" in the navigation or source status bar, **Then** a modal form opens displaying input fields for Target URL, Category, Source Name, Sample Link, VIP/Auth requirement, and Notes.
2. **Given** the form is open with a valid URL (e.g., `https://example-movies.ir`) and selected category `Movies/Series`, **When** the user clicks "Submit", **Then** the submission is accepted, the form closes or resets, and an immediate success toast is shown.
3. **Given** the form is open, **When** the user attempts to submit without a URL or without selecting a category, **Then** the submission is blocked and the missing required fields are highlighted.

---

### User Story 2 - Duplicate Suggestion Handling and Upvoting (Priority: P2)

When multiple users submit the same website domain, the system recognizes the existing entry and increments its interest counter instead of creating duplicate records or throwing an error.

**Why this priority**: Prevents database clutter and turns individual submissions into a quantified popularity signal, helping maintainers prioritize which sources have the highest user demand.

**Independent Test**: Submit the same source URL twice from different sessions and verify that the database retains a single entry with an incremented request counter.

**Acceptance Scenarios**:

1. **Given** a source `https://movies-share.ir` has already been submitted once (request count = 1), **When** a user submits `https://movies-share.ir/archive` or `http://www.movies-share.ir`, **Then** the submission succeeds with a standard confirmation, and the stored record's request count increases to 2.
2. **Given** an existing source record, **When** an additional submission includes new optional notes or sample links, **Then** the record's request count increments and its last-submitted timestamp updates.

---

### User Story 3 - Abuse Prevention and Rate Limiting (Priority: P3)

The submission intake is protected against flooding and automated spam scripts by enforcing a daily quota per client identifier.

**Why this priority**: Protects backend service and database storage from spam bots and malicious floods without requiring invasive user registration or captchas.

**Independent Test**: Send 10 consecutive submissions from a single client, then attempt an 11th and verify that it is rejected with a rate limit message.

**Acceptance Scenarios**:

1. **Given** a client has submitted 10 requests within a rolling 24-hour period, **When** that client attempts an 11th submission, **Then** the system rejects the submission with a friendly rate limit notification indicating the daily limit has been reached.
2. **Given** 24 hours have elapsed since earlier submissions, **When** the client submits a new source, **Then** the submission is accepted.

---

### User Story 4 - Maintainer Review and Triage of Submissions (Priority: P4)

Maintainers need a simple, authenticated method to review submitted suggestions, sort them by user demand (request count), and check their review status.

**Why this priority**: Ensures submitted suggestions can actually be reviewed and actioned by developers building scrapers.

**Independent Test**: Query the suggestions list with and without valid maintainer credentials to confirm authorization and verify returned data.

**Acceptance Scenarios**:

1. **Given** valid maintainer authorization credentials, **When** the maintainer requests the source suggestions list, **Then** all recorded suggestions are returned sorted by request count and recency, including review statuses (`pending`, `reviewed`, `implemented`, `rejected`).
2. **Given** invalid or missing credentials, **When** a client requests the suggestions list, **Then** access is denied with an unauthorized response.

---

### Edge Cases

- **Malformed URL Protocol**: User inputs `ftp://...`, `javascript:...`, or a plain string without a protocol. System must reject non-HTTP(S) inputs and prompt for a valid web link.
- **Subdomain Variations**: User inputs `https://sub.domain.com/` vs `https://domain.com/`. System normalizes domains to prevent splitting request counts across identical hosts.
- **Already Supported Source**: User suggests a source that is already an active scraper (e.g. `uptvs.com`). System informs the user that this source is already indexed and supported.
- **Oversized Text Inputs**: User inputs thousands of characters into optional notes. System enforces maximum length constraints (e.g., 500 characters) to prevent storage abuse.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an accessible user interface to submit source suggestions from the web application.
- **FR-002**: System MUST require a valid website URL and a media category (Movies/Series, Games, or Music) for every submission.
- **FR-003**: System MUST provide optional submission fields for Source Name, Sample Download URL, Notes, and a VIP/Account Required indicator.
- **FR-004**: System MUST validate that submitted URLs use `http` or `https` protocols and represent well-formed host addresses.
- **FR-005**: System MUST extract a canonical domain from the submitted URL and check for existing records; if matching, it MUST increment the `request_count` and update the `last_submitted_at` timestamp.
- **FR-006**: System MUST enforce a rate limit of at most 10 submissions per 24-hour window per client.
- **FR-007**: System MUST provide immediate, clear visual feedback (success toast notification) to the submitter upon completion.
- **FR-008**: System MUST persist suggestions with an initial review status of `pending`.
- **FR-009**: System MUST support tracking review status values: `pending`, `reviewed`, `implemented`, and `rejected`.
- **FR-010**: System MUST restrict retrieval of the source suggestions list to authorized maintainers only.
- **FR-011**: System MUST check submissions against currently active sources and notify the user if the source is already active.

### Key Entities *(include if feature involves data)*

- **SourceSuggestion**:
  - `id`: Unique identifier for the suggestion record.
  - `domain`: Canonical normalized domain of the source (e.g., `example.com`).
  - `url`: Original submitted web address.
  - `category`: Primary media type (`movies`, `games`, or `music`).
  - `source_name`: Optional human-friendly name.
  - `sample_url`: Optional sample download/post URL.
  - `notes`: Optional user commentary or instructions.
  - `requires_auth`: Boolean flag indicating if the source requires login or VIP membership.
  - `request_count`: Integer count of total user requests for this domain.
  - `status`: Current lifecycle state (`pending`, `reviewed`, `implemented`, `rejected`).
  - `first_submitted_at`: Timestamp of initial submission.
  - `last_submitted_at`: Timestamp of most recent submission.

- **RateLimitRecord**:
  - `client_id`: Hashed client identifier (e.g. client IP hash).
  - `timestamp`: Time of submission attempt.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete and submit a source suggestion in under 45 seconds from the web interface.
- **SC-002**: 100% of duplicate submissions for an existing source domain increment the request count without creating duplicate records.
- **SC-003**: 100% of malformed URLs, non-HTTP(S) protocols, and quota-exceeded requests are blocked with user-intelligible error feedback.
- **SC-004**: Authorized maintainers can retrieve the complete prioritized suggestions list in under 1 second.
- **SC-005**: Zero disruption or latency impact on existing search queries, filtering, or media streaming functionality.

## Assumptions

- Submitting users are anonymous consumers using standard desktop or mobile web browsers.
- Client IP addresses are accessible via standard network request context or trusted proxy headers for daily quota enforcement.
- Maintainers will review suggestions via authenticated API calls or database inspection without requiring a dedicated graphical management dashboard.
- Domain extraction standardizes `www.` prefixes and paths so that variations of the same root site coalesce into a single suggestion entity.
