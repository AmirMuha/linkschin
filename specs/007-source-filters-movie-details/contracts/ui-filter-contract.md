# UI Contract: InView Filter Bar, Badges, and URL State Synchronization

**Branch**: `007-source-filters-movie-details` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

This contract defines the UI component interfaces, badge display conventions, and URL synchronization contract for client-side filtering.

---

## 1. URL State Specification

Filter options are synchronized to browser URL query parameters without reloading the page.

| URL Query Parameter | Permitted Values | Default Value | Example URL |
|---------------------|------------------|---------------|-------------|
| `tier` | `all`, `free`, `premium` | `all` (omitted if default) | `/?q=batman&tier=free` |
| `censorship` | `all`, `uncensored`, `censored` | `all` (omitted if default) | `/?q=batman&censorship=uncensored` |

When both parameters are non-default:
`/?q=batman&category=movies&tier=free&censorship=uncensored`

---

## 2. Component Interface: `InViewFilterBar`

**Path**: `apps/web/src/components/InViewFilterBar.tsx`

```typescript
export interface FilterState {
  qualities: string[]
  audioTracks: string[]
  sources: string[]
  accessTier: 'all' | 'free' | 'premium'
  censorship: 'all' | 'uncensored' | 'censored'
}

export interface InViewFilterBarProps {
  availableQualities: string[]
  availableAudioTracks: string[]
  availableSources: { id: string; name: string }[]
  filters: FilterState
  onFilterChange: (filters: FilterState) => void
  showMovieFilters?: boolean  // Display tier and censorship chips only for movies category
}
```

### Visual Rendering Elements

1. **Access Tier Filter Group**:
   - Header: `دسترسی:`
   - Chips:
     - `همه` (`tier === 'all'`)
     - `فقط رایگان` (`tier === 'free'`) - Cyan active token
     - `فقط اشتراکی / VIP` (`tier === 'premium'`) - Amber active token
2. **Censorship Filter Group**:
   - Header: `سانسور:`
   - Chips:
     - `همه` (`censorship === 'all'`)
     - `بدون سانسور` (`censorship === 'uncensored'`) - Emerald active token
     - `سانسور شده` (`censorship === 'censored'`) - Amber active token

---

## 3. Component Interface: `MovieCard` Badges

**Path**: `apps/web/src/components/cards/MovieCard.tsx`

### Poster Overlay Badges

1. **IMDb Rating Badge** (Top-start corner or alongside Year badge):
   - Icon: Lucide `Star` (`fill-amber-400 text-amber-400 w-3 h-3`)
   - Text: `item.imdb_rating ? item.imdb_rating.toFixed(1) : '—'`
   - Styling: `bg-zinc-950/80 border border-zinc-800/80 font-mono text-2xs text-amber-300 backdrop-blur-md px-2 py-0.5 rounded-full`
2. **Censorship Badge** (Bottom or header overlay):
   - `uncensored`: `bg-emerald-950/80 text-emerald-300 border-emerald-800/60` (نسخه کامل)
   - `censored`: `bg-amber-950/80 text-amber-300 border-amber-800/60` (بازبینی شده)
   - `mixed`: `bg-cyan-950/80 text-cyan-300 border-cyan-800/60` (شامل هر دو نسخه)
   - `unspecified`: Hidden or subtle neutral gray pill `bg-zinc-900/80 text-zinc-400`
3. **Source Access Tier Badge**:
   - `free`: Subtle or default pill (`رایگان`)
   - `premium`: `bg-amber-500/20 text-amber-300 border-amber-500/40` (`VIP`)
   - `freemium`: `bg-cyan-500/20 text-cyan-300 border-cyan-500/40` (`ترکیبی`)

---

## 4. Component Interface: `MovieDownloadMatrix`

**Path**: `apps/web/src/components/cards/MovieDownloadMatrix.tsx`

```typescript
export interface MovieDownloadMatrixProps {
  variants: MovieDownloadVariant[]
  activeTierFilter?: 'all' | 'free' | 'premium'
  activeCensorshipFilter?: 'all' | 'uncensored' | 'censored'
}
```

- Each variant row includes:
  - Resolution & Codec (e.g. `1080p x265`)
  - Audio/Dub/Sub (e.g. `دوبله فارسی`)
  - Censorship Tag (when movie is `mixed`: `بدون سانسور` or `سانسور شده`)
  - VIP Tag (when source is freemium or premium: `VIP`)
  - Direct Download Link Button
- When `activeTierFilter === 'free'`, variant rows where `is_premium === true` are filtered out.
- When `activeCensorshipFilter === 'uncensored'`, variant rows where `is_censored === true` are filtered out.
