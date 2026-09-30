// Client-side filter predicates for the results grid (spec 007, FR-011).
// Pure functions so they are testable with `node --test` — no React runtime needed.
// Freemium sources stay visible under either tier filter; only their rows are pruned.

import type { CensorshipFilter, TierFilter } from './urlFilters.ts'
import type { MediaItem, MovieDownloadVariant } from '../types/media.ts'

export function itemMatchesTier(item: MediaItem, tier: TierFilter): boolean {
  if (tier === 'all') return true
  if (tier === 'free') return item.source_access_tier !== 'premium'
  return item.source_access_tier !== 'free'
}

export function variantsForTier(
  variants: MovieDownloadVariant[],
  tier: TierFilter
): MovieDownloadVariant[] {
  if (tier === 'all') return variants
  if (tier === 'free') return variants.filter((v) => !v.is_premium)
  return variants.filter((v) => v.is_premium === true)
}

export function itemMatchesCensorship(
  item: MediaItem,
  censorship: CensorshipFilter
): boolean {
  if (censorship === 'all') return true
  if (censorship === 'uncensored') {
    return item.censorship_status === 'uncensored' || item.censorship_status === 'mixed'
  }
  return item.censorship_status === 'censored' || item.censorship_status === 'mixed'
}

export function variantsForCensorship(
  variants: MovieDownloadVariant[],
  censorship: CensorshipFilter
): MovieDownloadVariant[] {
  if (censorship === 'all') return variants
  const wantCensored = censorship === 'censored'
  return variants.filter((v) => v.is_censored === wantCensored)
}

/** Music only. An item matches when ANY of its tracks is by one of the artists. */
export function itemMatchesArtists(item: MediaItem, artists: string[]): boolean {
  if (artists.length === 0) return true
  return (item.music_tracks ?? []).some((t) => artists.includes(t.artist))
}

/** Music only. A track with no album never matches a selected album. */
export function itemMatchesAlbums(item: MediaItem, albums: string[]): boolean {
  if (albums.length === 0) return true
  return (item.music_tracks ?? []).some((t) => t.album != null && albums.includes(t.album))
}

/** Music only. An item matches when any of its tracks offers a selected bitrate. */
export function itemMatchesBitrates(item: MediaItem, bitrates: string[]): boolean {
  if (bitrates.length === 0) return true
  return (item.music_tracks ?? []).some((t) =>
    (t.downloads ?? []).some((d) => bitrates.includes(d.bitrate))
  )
}
