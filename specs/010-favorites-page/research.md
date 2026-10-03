# Research: Favorites Page

**Feature**: `010-favorites-page` | **Date**: 2026-10-03

## Decisions

- **Routing**: Next.js App Router `apps/web/src/app/favorites/page.tsx`. Rationale: matches existing `/sources`, `/youtube-to-mp3` pages. Alternatives: query-param tab rejected (spec demands standalone page).
- **State**: `useFavorites` hook + localStorage key `linkschin:favorites`. Rationale: same durability as current watchlist, zero backend. Alternatives: server store rejected (no accounts per spec).
- **Icon**: `Heart` from `lucide-react` (already installed). Rationale: zero new dep, FR-008 bookmark removal. Alternatives: custom SVG rejected.
- **Lookup**: reuse `getCatalogItemById`. Rationale: exists, handles all three cats. Alternatives: new index rejected.
- **Migration**: one-way copy `linkschin:watchlist` → `linkschin:favorites` + delete old key. Rationale: SC-003 zero loss. Alternatives: dual-write rejected (retire old store).
