---
description: "Task list template for feature implementation"
---

# Tasks: YouTube to MP3 Downloader

**Input**: Design documents from `/specs/008-youtube-to-mp3/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/api.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Add `yt-dlp` dependency to backend in `apps/api/pyproject.toml`
- [ ] T002 Ensure `ffmpeg` is available or added to `apps/api/Dockerfile` for deployment

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Create `conversion_requests` table schema in `apps/api/db.py` (id, session_id, ip_address, youtube_url, video_title, status, file_path, error_message, created_at, completed_at)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Single Video Audio Extraction (Priority: P1) 🎯 MVP

**Goal**: Core extraction, convert, backend API + basic frontend form.

**Independent Test**: Paste a valid YouTube URL, convert, and successfully download an MP3.

### Implementation for User Story 1

- [ ] T004 [P] [US1] Create yt-dlp wrapper service in `apps/api/sources/yt_dlp_client.py` to handle extraction and conversion
- [ ] T005 [US1] Implement POST `/api/convert` endpoint in `apps/api/web/app.py` (validate URL, insert pending DB record, start background task)
- [ ] T006 [US1] Implement background task in `apps/api/web/app.py` to download via yt-dlp and update DB status (`processing` -> `completed`/`failed`)
- [ ] T007 [US1] Implement GET `/api/download/{request_id}` endpoint in `apps/api/web/app.py` to serve the resulting MP3 file
- [ ] T008 [P] [US1] Create frontend page layout in `apps/web/src/app/yt2mp3/page.tsx`
- [ ] T009 [US1] Create Downloader form component in `apps/web/src/components/Downloader.tsx` to accept URL and call POST `/api/convert`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Real-time Progress and Feedback (Priority: P2)

**Goal**: Provide UI progress updates while the conversion is running.

**Independent Test**: Submit a video and observe the UI updating through states (pending, processing, ready, failed).

### Implementation for User Story 2

- [ ] T010 [P] [US2] Implement GET `/api/convert/{request_id}` endpoint in `apps/api/web/app.py` to return current status and progress
- [ ] T011 [US2] Update yt-dlp wrapper in `apps/api/sources/yt_dlp_client.py` to capture download progress and update the DB record
- [ ] T012 [US2] Update `Downloader.tsx` in `apps/web/src/components/Downloader.tsx` to poll the status endpoint and display progress indicators

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Conversion History (Priority: P3)

**Goal**: Show a history of past conversions for the user session.

**Independent Test**: Convert a video, reload the page, and see the video listed in the history section.

### Implementation for User Story 3

- [ ] T013 [P] [US3] Implement GET `/api/convert/history` endpoint in `apps/api/web/app.py` to return recent requests for the user's session
- [ ] T014 [P] [US3] Create History list component in `apps/web/src/components/ConversionHistory.tsx`
- [ ] T015 [US3] Integrate `ConversionHistory` component into the main layout in `apps/web/src/app/yt2mp3/page.tsx`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: User Story 4 - Audio Metadata Enrichment (Priority: P4)

**Goal**: Embed ID3 tags (Title, Artist) into the downloaded MP3.

**Independent Test**: Downloaded MP3 file has correct title metadata in a media player.

### Implementation for User Story 4

- [ ] T016 [US4] Update yt-dlp configuration in `apps/api/sources/yt_dlp_client.py` to extract metadata and embed ID3 tags during ffmpeg conversion
- [ ] T017 [US4] Ensure file name sanitization based on video title in `apps/api/web/app.py` background task

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T018 Implement 20/hr/IP rate limiting for POST `/api/convert` in `apps/api/web/app.py` (Rule: Count requests for IP where created_at > now - 1 hour)
- [ ] T019 Implement maximum video length limit (20 mins) validation in `apps/api/sources/yt_dlp_client.py`
- [ ] T020 [P] Add backend unit tests for endpoints in `apps/api/tests/test_yt2mp3.py`
- [ ] T021 [P] Run `quickstart.md` validation scenarios manually to ensure E2E success

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can proceed in priority order (P1 → P2 → P3 → P4)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2).
- **User Story 2 (P2)**: Extends US1 (adds progress to downloader/API).
- **User Story 3 (P3)**: Can be developed in parallel to US2.
- **User Story 4 (P4)**: Depends on US1 completion.

### Parallel Opportunities

- Foundational tasks can be done alongside basic frontend scaffolding.
- US1 backend endpoints (T005-T007) and frontend component (T008-T009) can be developed in parallel by mocking the API on the frontend.
- US3 history component (T014) can be built in parallel to the backend history endpoint (T013).

---

## Parallel Example: User Story 1

```bash
# Backend dev:
Task: "[US1] Create yt-dlp wrapper service in apps/api/sources/yt_dlp_client.py"
Task: "[US1] Implement POST /api/convert endpoint in apps/api/web/app.py"

# Frontend dev:
Task: "[US1] Create frontend page layout in apps/web/src/app/yt2mp3/page.tsx"
Task: "[US1] Create Downloader form component in apps/web/src/components/Downloader.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add User Story 4 → Test independently → Deploy/Demo
6. Each story adds value without breaking previous stories