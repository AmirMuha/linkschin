---
# Implementation Plan: YouTube to MP3 Downloader

**Branch**: `008-youtube-to-mp3` | **Date**: 2026-10-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-youtube-to-mp3/spec.md`

## Summary

Implement a full-stack feature allowing users to paste a YouTube URL and download the audio track as an MP3 file, with real-time conversion progress, a history of past conversions, and strict rate limiting (20/hr/IP). The technical approach uses Python's FastAPI backend invoking `yt-dlp` for extraction and `ffmpeg` for MP3 conversion, storing request state and history in the existing SQLite database.

## Technical Context

**Language/Version**: Python 3 (Backend) / TypeScript (Frontend)

**Primary Dependencies**: FastAPI, `yt-dlp` (via subprocess or python package), Next.js, React

**Storage**: SQLite

**Testing**: `pytest` + `respx` (backend), Playwright (e2e frontend)

**Target Platform**: Linux server, modern web browsers

**Project Type**: Web Application (Backend API + Frontend UI)

**Performance Goals**: Accept conversion requests instantly; process 3-min video under 30s.

**Constraints**: Strict rate limiting (20/hr/IP), max video length (20 mins).

**Scale/Scope**: Moderate throughput, bounded by server CPU/bandwidth capacity for `ffmpeg`/downloading.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Library / Module Isolation**: The yt-dlp downloader will be placed cleanly in `apps/api/sources/` or as a distinct service module.
- **II. Simplicity / YAGNI**: We use the existing SQLite database for request tracking and rate limiting instead of adding Redis or Celery. We use API polling instead of WebSockets.
- **III. No Media Relaying**: **VIOLATION** - This feature fundamentally requires downloading and converting media on the server. We have documented this as an explicit exception in the specification.
- **IV. Testability**: The API endpoints will be tested using `respx` to mock YouTube responses and `yt-dlp` calls will be mocked.

## Project Structure

### Documentation (this feature)

```text
specs/008-youtube-to-mp3/
├── plan.md              
├── research.md          
├── data-model.md        
├── quickstart.md        
├── contracts/           
└── tasks.md             
```

### Source Code (repository root)

```text
apps/api/
├── db.py                 # Add SQLite schema for conversion_requests
├── sources/
│   └── yt_dlp.py         # The yt-dlp wrapper / downloader logic
├── web/
│   └── app.py            # Add FastAPI routes (/api/convert, /api/download)
└── tests/
    └── test_yt2mp3.py    # Unit tests for the endpoints and downloader

apps/web/
├── src/
│   ├── app/
│   │   └── yt2mp3/
│   │       └── page.tsx  # The main UI page for the downloader
│   └── components/
│       └── Downloader.tsx # Component handling form and polling
```

**Structure Decision**: Web application monorepo format matching the existing layout (`apps/api` for Python backend, `apps/web` for Next.js frontend).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Constitution III: No Media Relaying | MP3 conversion inherently requires server-side downloading and `ffmpeg` processing. | Client-side WASM ffmpeg is too heavy for standard web users and is prone to CORS/streaming issues with YouTube. The spec explicitly relaxed the rule for this feature. |