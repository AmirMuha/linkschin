'use client'

import React from 'react'
import type { CensorshipFilter, TierFilter } from '@/lib/urlFilters'
import type { Category } from '@/types/media'
import { Filter, X } from 'lucide-react'

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

const TIER_CHIPS: { value: TierFilter; label: string; active: string }[] = [
  { value: 'all', label: 'همه', active: 'bg-zinc-700/60 border-zinc-600/60 text-zinc-200' },
  { value: 'free', label: 'فقط رایگان', active: 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300' },
  { value: 'premium', label: 'فقط اشتراکی / VIP', active: 'bg-amber-500/20 border-amber-500/50 text-amber-300' },
]

const CENSORSHIP_CHIPS: { value: CensorshipFilter; label: string; active: string }[] = [
  { value: 'all', label: 'همه', active: 'bg-zinc-700/60 border-zinc-600/60 text-zinc-200' },
  { value: 'uncensored', label: 'بدون سانسور', active: 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300' },
  { value: 'censored', label: 'سانسور شده', active: 'bg-amber-500/20 border-amber-500/50 text-amber-300' },
]

const IDLE = 'bg-zinc-800/60 border-zinc-700/60 text-zinc-400 hover:text-zinc-200'

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

  const hasActiveFilters =
    filters.qualities.length > 0 ||
    filters.audioTracks.length > 0 ||
    filters.artists.length > 0 ||
    filters.albums.length > 0 ||
    filters.bitrates.length > 0 ||
    filters.sources.length > 0 ||
    filters.accessTier !== 'all' ||
    filters.censorship !== 'all'

  function toggleIn(key: 'qualities' | 'audioTracks' | 'artists' | 'albums' | 'bitrates' | 'sources', value: string) {
    const current = filters[key]
    onFilterChange({
      ...filters,
      [key]: current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value],
    })
  }

  function handleReset() {
    onFilterChange({ ...EMPTY_FILTERS })
  }

  // One table for the multi-select chip groups. Category decides which rows are
  // in play: quality/audio are movie-only, artist/album/bitrate are music-only,
  // and source is always offered when there is more than one.
  const chipGroups: {
    label: string
    options: { id: string; text: string }[]
    active: string
    toggle: (id: string) => void
    isActive: (id: string) => boolean
  }[] = []
  const group = (
    label: string,
    options: string[],
    active: string,
    key: 'qualities' | 'audioTracks' | 'artists' | 'albums' | 'bitrates'
  ) => {
    if (options.length === 0) return
    chipGroups.push({
      label,
      options: options.map((v) => ({ id: v, text: v })),
      active,
      toggle: (v) => toggleIn(key, v),
      isActive: (v) => filters[key].includes(v),
    })
  }
  if (isMovie) {
    group('کیفیت', availableQualities, 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300', 'qualities')
    group('صدا / زیرنویس', availableAudioTracks, 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300', 'audioTracks')
  }
  if (category === 'music') {
    group('خواننده', availableArtists, 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300', 'artists')
    group('آلبوم', availableAlbums, 'bg-violet-500/20 border-violet-500/50 text-violet-300', 'albums')
    group('بیت‌ریت', availableBitrates, 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300', 'bitrates')
  }
  if (availableSources.length > 1) {
    chipGroups.push({
      label: 'منبع',
      options: availableSources.map((s) => ({ id: s.id, text: s.name })),
      active: 'bg-violet-500/20 border-violet-500/50 text-violet-300',
      toggle: (id) => toggleIn('sources', id),
      isActive: (id) => filters.sources.includes(id),
    })
  }

  // Only render if there are options to filter by
  if (
    !isMovie &&
    availableArtists.length === 0 &&
    availableAlbums.length === 0 &&
    availableBitrates.length === 0 &&
    availableSources.length <= 1
  ) {
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

        <div className="flex items-center gap-3">
          {hasActiveFilters && (
            <button
              type="button"
              onClick={handleReset}
              className="flex items-center gap-1 text-xs text-zinc-400 hover:text-rose-400 transition-colors"
            >
              <X className="w-3.5 h-3.5" />
              <span>حذف تمام فیلترها</span>
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center flex-wrap gap-4 text-xs">
        {chipGroups.map((row) => (
          <div key={row.label} className="flex items-center flex-wrap gap-1.5">
            <span className="text-zinc-500 font-medium">{row.label}:</span>
            {row.options.map((opt) => {
              const active = row.isActive(opt.id)
              return (
                <button
                  key={opt.id}
                  type="button"
                  aria-pressed={active}
                  onClick={() => row.toggle(opt.id)}
                  className={`px-2.5 py-1 rounded-lg border font-medium transition-colors ${
                    active ? row.active : IDLE
                  }`}
                >
                  {opt.text}
                </button>
              )
            })}
          </div>
        ))}

        {/* Single-select chips — movies only */}
        {isMovie && (
          <>
            <div className="flex items-center flex-wrap gap-1.5">
              <span className="text-zinc-500 font-medium">دسترسی:</span>
              {TIER_CHIPS.map((chip) => {
                const active = filters.accessTier === chip.value
                return (
                  <button
                    key={chip.value}
                    type="button"
                    aria-pressed={active}
                    onClick={() => onFilterChange({ ...filters, accessTier: chip.value })}
                    className={`px-2.5 py-1 rounded-lg border font-medium transition-colors ${active ? chip.active : IDLE}`}
                  >
                    {chip.label}
                  </button>
                )
              })}
            </div>

            <div className="flex items-center flex-wrap gap-1.5">
              <span className="text-zinc-500 font-medium">سانسور:</span>
              {CENSORSHIP_CHIPS.map((chip) => {
                const active = filters.censorship === chip.value
                return (
                  <button
                    key={chip.value}
                    type="button"
                    aria-pressed={active}
                    onClick={() => onFilterChange({ ...filters, censorship: chip.value })}
                    className={`px-2.5 py-1 rounded-lg border font-medium transition-colors ${active ? chip.active : IDLE}`}
                  >
                    {chip.label}
                  </button>
                )
              })}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
