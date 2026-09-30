# Problem Definition: Irrelevant Search Results in Scraper Pipeline

- **Slug**: search-result-relevance
- **Created**: 2026-09-30
- **Inputs used**: intake.md, research.md, test fixtures

## Problem Statement

When users search for movies, the search results grid displays irrelevant, unrelated titles (such as "سیلو", "باب اسفنجی", and "From") alongside valid hits. This occurs because the UpTVs scraper parses global anchor tags across the entire HTML response rather than scoping extraction to the search result card container, accidentally capturing hardcoded links within the site's search modal navigation widget. Additionally, search results lack poster images because the scraper ignores thumbnail images present in the search DOM.

## Affected Users & Stakeholders

- **End Users**: Receive noisy, incorrect search results and missing poster artwork, harming trust in search relevance.
- **Maintainers**: Database and cache get polluted with unrelated media items on every query.

## Goals

1. Eliminate all noise items (specifically search modal and navigation links) from UpTVs search extraction.
2. Scope UpTVs item parsing strictly to search result card blocks (`div.content-thumb` or by excluding `uas_search_modal`).
3. Extract poster thumbnail URLs during search result parsing in `UpTVsPlugin` so cards display movie posters immediately.
4. Add a defensive relevance guard at the scraper or collection layer to filter out any future unindexed/spurious items.

## Non-Goals

- Changing external search engine behavior of upstream sites.
- Implementing AI/ML semantic ranking models.
- Rewriting scrapers for unrelated sources that are already container-scoped.

## Success Metrics

- 0 unrelated/navigation items returned in UpTVs search results across all test queries.
- UpTVs search fixture tests pass with 15 real items extracted (0 from modal).
- 100% of UpTVs search results populate `poster_url` when thumbnails are present.
- All 53 existing pytest tests pass.

## Cost of Inaction

Users searching for any movie continue to see "Silo", "SpongeBob", and "From" at the bottom of their results grid with broken thumbnails.
