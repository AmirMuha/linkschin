# Idea Intake: Fix Irrelevant Search Results from Upstream Scrapers

- **Slug**: search-result-relevance
- **Created**: 2026-09-30
- **Source**: user bug report with screenshot
- **Type**: defect

## Idea / Bug Report (as captured)

> "the scraper also includes irrelavent movies in the search results [Image #1] e.g. I search for spiderman and got silo,from,and sponge bob too in the results /speckit.bug.assess"

## Restated

Searching for specific movies (such as "spiderman") returns unrelated media items ("سیلو" / Silo, "باب اسفنجی" / SpongeBob, "From") in the search results grid alongside valid matches. Search results also lack poster thumbnails ("بدون تصویر").

## Origin & Context

- **Raised by**: amirmuha
- **Trigger**: User tested search query "spiderman" on web UI; results included cards for Silo, SpongeBob, and From from source `uptvs`.
- **Affected Surface**: `apps/api/sources/movies/uptvs.py`, `apps/api/web/app.py`, `apps/web/src/app/page.tsx`.

## Clarifications & Scope

- **Root Cause Identified**: `UpTVsPlugin.parse_search_results` uses an unanchored global regex matching all `/contents/` links with a `title` attribute. The UpTVs website layout includes a persistent search modal (`div.uas_search_modal__categories`) containing static suggested category/content links ("سیلو", "باب اسفنجی", "From"). These are parsed on every query.
- **Secondary Defects**:
  1. `UpTVsPlugin` does not extract poster images in `parse_search_results`, causing cards to display "بدون تصویر".
  2. Aggregation layer (`_collect_items`) does not perform relevance filtering on scraper results before caching/serving.

## First-Glance Unknowns

None. Verified directly against `uptvs_search.html` fixture and upstream DOM structure.
