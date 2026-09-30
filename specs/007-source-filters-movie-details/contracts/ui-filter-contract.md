# UI Contract: InView Filter Bar, Badges, and URL State Synchronization

**Branch**: `007-source-filters-movie-details` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

This contract defines the UI component interfaces, badge display conventions, and URL synchronization contract for client-side filtering.

---

## 1. URL State Specification

Filter options are synchronized to browser URL query parameters without reloading the page (`window.history.replaceState` in `apps/web/src/app/page.tsx`). Parsers are strict: any value outside the permitted set falls back to `'all'` (`apps/web/src/lib/urlFilters.ts`), and unrelated query parameters (`q`, `category`) are preserved when writing.

| URL Query Parameter | Permitted Values | Default Value | Example URL |
|---------------------|------------------|---------------|-------------|
| `tier` | `all`, `free`, `premium` | `all` (omitted if default) | `/?q=batman&tier=free` |
| `censorship` | `all`, `uncensored`, `censored` | `all` (omitted if default) | `/?q=batman&censorship=uncensored` |

When both parameters are non-default:
`/?q=batman&category=movies&tier=free&censorship=uncensored`

Note: `mixed` is a valid item-level `censorship_status` but NOT a URL filter value — each strict filter keeps `mixed` items (see §5).

---

## 2. Component Interface: `InViewFilterBar`

**Path**: `apps/web/src/components/InViewFilterBar.tsx`

```typescript
import type { CensorshipFilter, TierFilter } from '@/lib/urlFilters'

export interface FilterState {
  qualities: string[]
  audioTracks: string[]
  sources: string[]
  accessTier: TierFilter          // 'all' | 'free' | 'premium'
  censorship: CensorshipFilter    // 'all' | 'uncensored' | 'censored'
}

export interface InViewFilterBarProps {
  availableQualities: string[]
  availableAudioTracks: string[]
  availableSources: { id: string; name: string }[]
  filters: FilterState
  onFilterChange: (filters: FilterState) => void
  showMovieFilters?: boolean  // defaults true; page.tsx passes `category === 'movies'`
}
```

### Visual Rendering Elements

Chip groups render in order: quality (`کیفیت:`), audio (`صدا / زیرنویس:`), source
(`منبع:`), then the two movie-only groups below (rendered only when
`showMovieFilters` is true). Tier/censorship chips carry `aria-pressed`.

1. **Access Tier Filter Group** (`TIER_CHIPS`, order: all → free → premium):
   - Header: `دسترسی:`
   - Chips:
     - `همه` (`tier === 'all'`) — active: `bg-zinc-700/60 border-zinc-600/60 text-zinc-200`
     - `فقط رایگان` (`tier === 'free'`) — active cyan: `bg-cyan-500/20 border-cyan-500/50 text-cyan-300`
     - `فقط اشتراکی / VIP` (`tier === 'premium'`) — active amber: `bg-amber-500/20 border-amber-500/50 text-amber-300`
2. **Censorship Filter Group** (`CENSORSHIP_CHIPS`, order: all → uncensored → censored):
   - Header: `سانسور:`
   - Chips:
     - `همه` (`censorship === 'all'`) — active: `bg-zinc-700/60 border-zinc-600/60 text-zinc-200`
     - `بدون سانسور` (`censorship === 'uncensored'`) — active emerald: `bg-emerald-500/20 border-emerald-500/50 text-emerald-300`
     - `سانسور شده` (`censorship === 'censored'`) — active amber: `bg-amber-500/20 border-amber-500/50 text-amber-300`

Idle chip class for both groups: `bg-zinc-800/60 border-zinc-700/60 text-zinc-400 hover:text-zinc-200`.

**Reset**: button `حذف تمام فیلترها` renders whenever any group is non-default
(`hasActiveFilters` includes `accessTier !== 'all' || censorship !== 'all'`) and clears
all five `FilterState` keys back to their defaults.

---

## 3. Component Interface: `MovieCard` Badges

**Path**: `apps/web/src/components/cards/MovieCard.tsx`

All overlay badges render unconditionally (no layout shift for null/unspecified data;
SC-002). RTL logical positions: source badge top-start, year badge top-end, IMDb badge
bottom-start, censorship badge bottom-start above IMDb (`bottom-11`), tier badge
bottom-end.

### Poster Overlay Badges

1. **IMDb Rating Badge** (bottom-start, always present):
   - Icon: Lucide `Star` (`w-3 h-3 fill-amber-400 text-amber-400`)
   - Text: `item.imdb_rating?.toFixed(1) ?? '—'`
   - Styling: `bg-zinc-950/80 border border-zinc-800/80 font-mono text-2xs text-amber-300 backdrop-blur-md px-2 py-0.5 rounded-full`
2. **Censorship Badge** (`CENSORSHIP_BADGE` map, always shown):
   - `uncensored`: `bg-emerald-950/80 text-emerald-300 border-emerald-800/60` (نسخه کامل)
   - `censored`: `bg-amber-950/80 text-amber-300 border-amber-800/60` (بازبینی شده)
   - `mixed`: `bg-cyan-950/80 text-cyan-300 border-cyan-800/60` (شامل هر دو نسخه)
   - `unspecified`: shown as a neutral gray pill `bg-zinc-900/80 text-zinc-400 border-zinc-700/60` (نامشخص) — never hidden, never coerced to another status
3. **Source Access Tier Badge** (`TIER_BADGE` map, always shown):
   - `free`: `bg-zinc-950/80 text-zinc-300 border-zinc-800/80` (رایگان)
   - `premium`: `bg-amber-500/20 text-amber-300 border-amber-500/40` (VIP)
   - `freemium`: `bg-cyan-500/20 text-cyan-300 border-cyan-500/40` (ترکیبی)

---

## 4. Component Interface: `MovieDownloadMatrix`

**Path**: `apps/web/src/components/cards/MovieDownloadMatrix.tsx`

```typescript
import type { CensorshipFilter, TierFilter } from '@/lib/urlFilters'

export interface MovieDownloadMatrixProps {
  variants: MovieDownloadVariant[]
  activeTierFilter?: TierFilter              // default 'all'
  activeCensorshipFilter?: CensorshipFilter  // default 'all'
}
```

Visible rows = `variantsForCensorship(variantsForTier(variants, tier), censorship)`
from `apps/web/src/lib/filters.ts`. Tags render per-variant regardless of the item's
`censorship_status`:

- `is_censored === true`: amber tag `سانسور شده` (`bg-amber-500/20 text-amber-300`)
- `is_censored === false`: emerald tag `بدون سانسور` (`bg-emerald-500/20 text-emerald-300`)
- `is_censored == null`: no tag (the source declared nothing)
- `is_premium === true`: bold amber tag `VIP` (`bg-amber-500/20 text-amber-300 font-bold`)

Row pruning (real semantics):

- `tier === 'free'` keeps only rows where `is_premium` is falsy; `tier === 'premium'` keeps only rows where `is_premium === true`; `'all'` returns the input array untouched (identity preserved).
- `censorship === 'uncensored'` keeps only rows where `is_censored === false` — rows with `is_censored === true` AND rows with `is_censored == null` are both hidden.
- `censorship === 'censored'` keeps only rows where `is_censored === true` — `false` and `null` rows hidden.

When every row is pruned, the matrix shows: `هیچ لینکی با فیلترهای فعلی مطابقت ندارد.`

---

## 5. Filter Evaluation Semantics (implemented in `apps/web/src/lib/filters.ts`)

Item-level rules — freemium sources stay visible under EITHER tier filter; only their
download rows are pruned:

- `itemMatchesTier`: `'free'` keeps items with `source_access_tier !== 'premium'` (free + freemium); `'premium'` keeps items with `source_access_tier !== 'free'` (premium + freemium); `'all'` passes everything.
- `itemMatchesCensorship`: `'uncensored'` keeps `uncensored` + `mixed`, drops `censored` + `unspecified`; `'censored'` keeps `censored` + `mixed`, drops `uncensored` + `unspecified`; `'all'` passes everything.

---

## 6. Marker Vocabulary and Null Semantics (scraper contract)

- **A bare Persian `اشتراک` means "share" (`اشتراک گذاری`), NOT subscription.** Every item
  page on these portals carries share buttons labelled `اشتراک گذاری در فیسبوک/تلگرام/…`;
  matching bare `اشتراک` would mis-flag every link as paid. Only the composite
  `اشتراک ویژه` (plus `VIP` / `وی.آی.پی`) marks a paywall — see `_VIP_MARKERS` in
  `apps/api/sources/movies/uptvs.py` and `doostihaa.py`.
- **An absent censorship marker stays `is_censored: null` on the variant and
  `censorship_status = unspecified` on the item — never coerced to "uncensored"**
  (`_censorship_flag` returns `None`; `derive_censorship_status` returns `UNSPECIFIED`
  when no variant declares a flag; the strict censorship filters hide `null` rows rather
  than assume).
- Uncensored markers: `نسخه کامل`, `بدون سانسور`, `uncut`. Censored markers:
  `بازبینی شده`, `سانسور شده`, `نسخه سانسور` (`\s*`-tolerant spacing; case-insensitive
  for `uncut`/`VIP`).
- **Recorded fixture reality**: `uptvs_item.html` contains no censorship markers at all
  (every uptvs item stays `unspecified` with all-`null` variant flags);
  `doostihaa_item.html` carries a page-level `نسخه سانسور شده` tag, which seeds every
  variant lacking its own per-link marker (a per-link marker still wins where present).
