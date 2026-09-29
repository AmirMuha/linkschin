# Tasks: User Source Suggestion Form

**Input**: Design documents from `/specs/004-source-suggestions/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/suggestions-api.json`, `quickstart.md`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Define cross-stack schemas and shared types.

- [ ] T001 [P] Define TypeScript types `SourceSuggestionInput` and `SourceSuggestionResponse` in `apps/web/src/types/media.ts`
- [ ] T002 [P] Define Pydantic models `SourceSuggestionCreate`, `SourceSuggestionResponse`, and `SourceSuggestionAdminOut` in `apps/api/models.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database tables and shared utilities that block all user stories.

**⚠️ CRITICAL**: Must complete before user story implementation begins.

- [ ] T003 Add `source_suggestions` table (`domain TEXT NOT NULL UNIQUE`, `url TEXT NOT NULL`, `category TEXT NOT NULL`, `request_count INTEGER NOT NULL DEFAULT 1`, `status TEXT NOT NULL DEFAULT 'pending'`) and `suggestion_rate_limits` table to `SCHEMA` in `apps/api/db.py`
- [ ] T004 Implement URL canonical domain extraction helper `normalize_source_domain(url: str) -> str` in `apps/api/db.py`

**Checkpoint**: Foundation ready — database schema and domain extraction verified.

---

## Phase 3: User Story 1 - Suggesting a New Source via In-App Form (Priority: P1) 🎯 MVP

**Goal**: Enable users to open a modal form in the web UI, fill required URL and Category fields, and submit a suggestion to the API with success feedback.

**Independent Test**: Open suggestion form, enter valid URL (e.g. `https://film2media.click`) and category `movies`, submit, and confirm record is created with status `'pending'` and success toast appears.

### Tests for User Story 1

- [ ] T005 [P] [US1] Create unit and endpoint tests for suggestion submission in `apps/api/tests/test_suggestions.py`

### Implementation for User Story 1

- [ ] T006 [US1] Implement `create_source_suggestion` database insertion function in `apps/api/db.py`
- [ ] T007 [US1] Implement `POST /api/sources/suggest` endpoint validating category (`movies`, `games`, `music`) and URL in `apps/api/web/app.py`
- [ ] T008 [P] [US1] Implement `submitSourceSuggestion` client function calling `POST /api/sources/suggest` in `apps/web/src/lib/api.ts`
- [ ] T009 [US1] Create `SourceSuggestModal.tsx` with RTL layout, URL/category validation, and toast feedback in `apps/web/src/components/SourceSuggestModal.tsx`
- [ ] T010 [US1] Add "پیشنهاد منبع" (Suggest Source) trigger button to `SourceStatusBar.tsx` in `apps/web/src/components/SourceStatusBar.tsx`

**Checkpoint**: User Story 1 (MVP) is fully functional and testable end-to-end.

---

## Phase 4: User Story 2 - Duplicate Suggestion Handling and Upvoting (Priority: P2)

**Goal**: Automatically detect submissions for existing domains and increment `request_count` instead of creating duplicate records or erroring.

**Independent Test**: Submit the same website domain twice with different path variants and verify the database maintains a single row with `request_count = 2`.

### Tests for User Story 2

- [ ] T011 [P] [US2] Add duplicate domain upvote tests in `apps/api/tests/test_suggestions.py`

### Implementation for User Story 2

- [ ] T012 [US2] Update `save_or_upvote_source_suggestion` in `apps/api/db.py` to upsert and increment `request_count` on domain collision
- [ ] T013 [US2] Update `POST /api/sources/suggest` in `apps/api/web/app.py` to return `is_existing: true` and current `request_count`

**Checkpoint**: User Stories 1 and 2 operate seamlessly together.

---

## Phase 5: User Story 3 - Abuse Prevention and Rate Limiting (Priority: P3)

**Goal**: Limit client submissions to at most 10 per 24-hour window per IP address using SHA-256 IP hashing.

**Independent Test**: Send 11 submissions from a single client IP and verify the 11th attempt returns HTTP 429 Too Many Requests with a Persian error message.

### Tests for User Story 3

- [ ] T014 [P] [US3] Add rate limiting test cases verifying 10-per-day threshold and 429 response in `apps/api/tests/test_suggestions.py`

### Implementation for User Story 3

- [ ] T015 [US3] Implement `check_and_record_rate_limit(client_ip: str) -> bool` with 24-hour timestamp check in `apps/api/db.py`
- [ ] T016 [US3] Integrate rate limit verification into `POST /api/sources/suggest` in `apps/api/web/app.py`
- [ ] T017 [US3] Handle HTTP 429 rate limit error feedback in `SourceSuggestModal.tsx` in `apps/web/src/components/SourceSuggestModal.tsx`

**Checkpoint**: Rate limiting prevents flood attacks across restarts without external services.

---

## Phase 6: User Story 4 - Maintainer Review and Triage of Submissions (Priority: P4)

**Goal**: Provide an authenticated endpoint for maintainers to inspect, filter, and prioritize suggestions.

**Independent Test**: Call `GET /api/admin/suggestions` with and without `X-Admin-Token` header to verify authorization and response schema.

### Tests for User Story 4

- [ ] T018 [P] [US4] Add authentication and suggestion listing tests in `apps/api/tests/test_suggestions.py`

### Implementation for User Story 4

- [ ] T019 [US4] Implement `get_source_suggestions(status, category, limit)` query helper in `apps/api/db.py`
- [ ] T020 [US4] Implement `GET /api/admin/suggestions` endpoint protected by `X-Admin-Token` header in `apps/api/web/app.py`

**Checkpoint**: All 4 user stories functional and independently verified.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end verification and quality validation.

- [ ] T021 [P] Run end-to-end verification scenarios per `quickstart.md` using `curl` against local backend in `specs/004-source-suggestions/quickstart.md`
- [ ] T022 [P] Run full test suite with `pytest apps/api/tests/test_suggestions.py` and `pnpm --filter web lint`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Independent — can begin immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational completion — Delivers MVP.
- **User Story 2 (Phase 4)**: Depends on User Story 1.
- **User Story 3 (Phase 5)**: Depends on User Story 1.
- **User Story 4 (Phase 6)**: Depends on Foundational & US1 DB models.
- **Polish (Phase 7)**: Depends on all user stories completion.

### Parallel Opportunities

- T001 and T002 can run in parallel (frontend types & backend models).
- T005, T008 can run in parallel with backend implementation.
- T011, T014, T018 tests can be written in parallel once foundation is in place.
- T021 and T022 can run in parallel during final verification.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (T001-T002) and Phase 2 (T003-T004).
2. Complete Phase 3 (T005-T010).
3. **STOP and VALIDATE**: Test submission flow in UI and check SQLite database.
4. Deploy / demo MVP.

### Incremental Delivery

1. Foundation: Tables + domain extraction ready.
2. US1: Form + basic submission (MVP).
3. US2: Upvoting on duplicates.
4. US3: IP rate limiting (10/day).
5. US4: Admin triage endpoint (`X-Admin-Token`).
6. Polish: Validation scenarios.
