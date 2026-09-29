# Idea Intake: User Source Suggestion Form

- **Slug**: source-suggestions
- **Created**: 2026-09-29
- **Source**: pasted text
- **Type**: new-capability

## Idea (as captured)

> "submittable form for allowing users to suggest and request for sources they know"

## Restated

A submittable user-facing form allowing users to submit requests and suggestions for new media sources. Submissions collect source metadata to evaluate adding new scrapers to the platform.

## Origin & Context

- **Raised by**: User / product owner
- **Trigger**: Expanding scraper coverage by gathering source recommendations directly from users

## Clarifications & Scope

- **Required Fields**: Target site URL and Category (movies, games, music).
- **Optional Fields**: Source name, sample download link, notes, auth/VIP requirements.
- **Storage**: Local SQLite database table (`source_suggestions`) with tracking status (`pending`, `reviewed`, `implemented`, `rejected`) and upvote/request counter.
- **Abuse Prevention**: IP rate limiting at 10 submissions per day per client IP.
- **Duplicate Handling**: If target domain/URL is already submitted, increment the existing record's request count/upvote rather than creating duplicates or rejecting.
- **Admin Triage**: Protected API endpoint (`GET /api/admin/suggestions`) secured with an admin token or header.
- **User Feedback**: Immediate success toast notification in the UI; form resets; fire-and-forget (no public tracking ID needed).
- **Visibility**: Private intake for maintainers/admins; no public upvoting board.
- **UI Surface**: Web UI modal/drawer accessible from navigation or `SourceStatusBar`.

## First-Glance Unknowns

None remaining. All initial questions clarified.
