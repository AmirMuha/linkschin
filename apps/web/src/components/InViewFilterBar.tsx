'use client'

import React from 'react'
import type { CensorshipFilter, TierFilter } from '@/lib/urlFilters'
import type { Category } from '@/types/media'
import { Filter, X } from 'lucide-react'

// ponytail: multi-value filters stay arrays holding 0..1 entries, so switching
// back to chips later is a render change, not a state-shape change across
// filters.ts / page.tsx / urlFilters.ts.
export type MultiKey =
  | 'qualities'
  | 'audioTracks'
  | 'artists'
  | 'albums'
  | 'bitrates'
  | 'sources'

export interface FilterState {
  qualities: string[]
  audioTracks: string[]
  /** Music only — a track matches when any of its own tags intersects. */
  artists: string[]
  albums: string[]
  bitrates: string[]
  sources: string[]
  /** Persisted per-user hidden set; sent as repeated `sources=` params. */
  hiddenSources: string[]
  accessTier: TierFilter
  censorship: CensorshipFilter
}

export const EMPTY_FILTERS: FilterState = {
  qualities: [],
  audioTracks: [],
  artists: [],
  albums: [],
  bitrates: [],
  sources: [],
  hiddenSources: [],
  accessTier: 'all',
  censorship: 'all',
}

interface InViewFilterBarProps {
  category: Category
  availableQualities: string[]
  availableAudioTracks: string[]
  availableArtists: string[]
  availableAlbums: string[]
  availableBitrates: string[]
  availableSources: { id: string; name: string }[]
  filters: FilterState
  onFilterChange: (filters: FilterState) => void
}

const TIER_OPTIONS: { value: TierFilter; label: string }[] = [
  { value: 'all', label: 'همه' },
  { value: 'free', label: 'فقط رایگان' },
  { value: 'premium', label: 'فقط اشتراکی / VIP' },
]

const CENSORSHIP_OPTIONS: { value: CensorshipFilter; label: string }[] = [
  { value: 'all', label: 'همه' },
  { value: 'uncensored', label: 'بدون سانسور' },
  { value: 'censored', label: 'سانسور شده' },
]

// text-sm (14px) not text-xs: iOS zooms any form control under 16px on focus, so
// the small breakpoint only drops it once the viewport is wide enough that the
// zoom no longer applies. `option` is styled too — the popup list is painted by
// the UA, not the select, and inherits no colour in most browsers.
const SELECT_CLASS =
  'max-w-[10rem] min-h-11 sm:min-h-0 px-2 py-1.5 rounded-lg border border-zinc-700/60 ' +
  'bg-zinc-800 text-zinc-100 text-sm sm:text-xs focus:border-cyan-500 focus:outline-none ' +
  'focus:ring-1 focus:ring-cyan-500/30'

export function InViewFilterBar({
  category,
  availableQualities,
  availableAudioTracks,
  availableArtists,
  availableAlbums,
  availableBitrates,
  availableSources,
  filters,
  onFilterChange,
}: InViewFilterBarProps) {
  const isMovie = category === 'movies'

  // Category decides which selects are in play: quality/audio are movie-only,
  // artist/album/bitrate are music-only, source is offered once there are 2+.
  const selects: { label: string; options: { id: string; text: string }[]; key: MultiKey }[] = []
  const addSelect = (label: string, options: string[], key: MultiKey) => {
    if (options.length === 0) return
    selects.push({
      label,
      options: options.map((v) => ({ id: v, text: v })),
      key,
    })
  }
  if (isMovie) {
    addSelect('کیفیت', availableQualities, 'qualities')
    addSelect('صدا / زیرنویس', availableAudioTracks, 'audioTracks')
  }
  if (category === 'music') {
    addSelect('خواننده', availableArtists, 'artists')
    addSelect('آلبوم', availableAlbums, 'albums')
    addSelect('بیت‌ریت', availableBitrates, 'bitrates')
  }
  if (availableSources.length > 1) {
    selects.push({
      label: 'منبع',
      options: availableSources.map((s) => ({ id: s.id, text: s.name })),
      key: 'sources',
    })
  }

  const hasActiveFilters =
    selects.some((sel) => (filters[sel.key] ?? []).length > 0) ||
    filters.accessTier !== 'all' ||
    filters.censorship !== 'all'

  function selectIn(key: MultiKey, value: string) {
    onFilterChange({ ...filters, [key]: value ? [value] : [] })
  }

  // Only render if there is something to filter by
  if (!isMovie && selects.length === 0) {
    return null
  }

  return (
    <div
      role="region"
      aria-label="فیلتر نتایج جستجو"
      className="w-full flex flex-col gap-3 p-4 rounded-2xl bg-zinc-900/60 border border-zinc-800/80 backdrop-blur-md"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-zinc-300">
          <Filter className="w-4 h-4 text-cyan-400" />
          <span>فیلتر سریع نتایج</span>
        </div>

        {hasActiveFilters && (
          <button
            type="button"
            onClick={() => onFilterChange({ ...EMPTY_FILTERS })}
            className="flex items-center gap-1 text-xs text-zinc-400 hover:text-rose-400 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
            <span>حذف تمام فیلترها</span>
          </button>
        )}
      </div>

      <div className="flex items-center flex-wrap gap-x-4 gap-y-2 text-xs">
        {selects.map((sel) => (
          <label key={sel.key} className="flex items-center gap-1.5">
            <span className="text-zinc-500 font-medium">{sel.label}:</span>
            <select
              className={SELECT_CLASS}
              value={filters[sel.key][0] ?? ''}
              onChange={(e) => selectIn(sel.key, e.target.value)}
            >
              <option className="bg-zinc-900 text-zinc-100" value="">
                همه
              </option>
              {sel.options.map((opt) => (
                <option key={opt.id} className="bg-zinc-900 text-zinc-100" value={opt.id}>
                  {opt.text}
                </option>
              ))}
            </select>
          </label>
        ))}

        {/* Single-value selects — movies only */}
        {isMovie && (
          <>
            <label className="flex items-center gap-1.5">
              <span className="text-zinc-500 font-medium">دسترسی:</span>
              <select
                className={SELECT_CLASS}
                value={filters.accessTier}
                onChange={(e) =>
                  onFilterChange({ ...filters, accessTier: e.target.value as TierFilter })
                }
              >
                {TIER_OPTIONS.map((opt) => (
                  <option
                    key={opt.value}
                    className="bg-zinc-900 text-zinc-100"
                    value={opt.value}
                  >
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex items-center gap-1.5">
              <span className="text-zinc-500 font-medium">سانسور:</span>
              <select
                className={SELECT_CLASS}
                value={filters.censorship}
                onChange={(e) =>
                  onFilterChange({ ...filters, censorship: e.target.value as CensorshipFilter })
                }
              >
                {CENSORSHIP_OPTIONS.map((opt) => (
                  <option
                    key={opt.value}
                    className="bg-zinc-900 text-zinc-100"
                    value={opt.value}
                  >
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
          </>
        )}
      </div>
    </div>
  )
}