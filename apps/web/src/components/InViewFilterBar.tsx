'use client'

import React from 'react'
import type { CensorshipFilter, TierFilter } from '@/lib/urlFilters'
import { Filter, X } from 'lucide-react'

export interface FilterState {
  qualities: string[]
  audioTracks: string[]
  sources: string[]
  /** Persisted per-user hidden set; sent as repeated `sources=` params. */
  hiddenSources: string[]
  accessTier: TierFilter
  censorship: CensorshipFilter
}

interface InViewFilterBarProps {
  availableQualities: string[]
  availableAudioTracks: string[]
  availableSources: { id: string; name: string }[]
  filters: FilterState
  onFilterChange: (filters: FilterState) => void
  showMovieFilters?: boolean
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
  availableQualities,
  availableAudioTracks,
  availableSources,
  filters,
  onFilterChange,
  showMovieFilters = true,
}: InViewFilterBarProps) {
  const hasActiveFilters =
    filters.qualities.length > 0 ||
    filters.audioTracks.length > 0 ||
    filters.sources.length > 0 ||
    filters.accessTier !== 'all' ||
    filters.censorship !== 'all'

  function toggleQuality(q: string) {
    const exists = filters.qualities.includes(q)
    const next = exists
      ? filters.qualities.filter((item) => item !== q)
      : [...filters.qualities, q]
    onFilterChange({ ...filters, qualities: next })
  }

  function toggleAudio(a: string) {
    const exists = filters.audioTracks.includes(a)
    const next = exists
      ? filters.audioTracks.filter((item) => item !== a)
      : [...filters.audioTracks, a]
    onFilterChange({ ...filters, audioTracks: next })
  }

  function toggleSource(s: string) {
    const exists = filters.sources.includes(s)
    const next = exists
      ? filters.sources.filter((item) => item !== s)
      : [...filters.sources, s]
    onFilterChange({ ...filters, sources: next })
  }

  function handleReset() {
    onFilterChange({
      qualities: [],
      audioTracks: [],
      sources: [],
      hiddenSources: [],
      accessTier: 'all',
      censorship: 'all',
    })
  }

  // Only render if there are options to filter by
  if (
    !showMovieFilters &&
    availableQualities.length === 0 &&
    availableAudioTracks.length === 0 &&
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
        {/* Quality Chips */}
        {availableQualities.length > 0 && (
          <div className="flex items-center flex-wrap gap-1.5">
            <span className="text-zinc-500 font-medium">کیفیت:</span>
            {availableQualities.map((q) => {
              const active = filters.qualities.includes(q)
              return (
                <button
                  key={q}
                  type="button"
                  onClick={() => toggleQuality(q)}
                  className={`px-2.5 py-1 rounded-lg border font-mono font-medium transition-colors ${
                    active
                      ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300'
                      : 'bg-zinc-800/60 border-zinc-700/60 text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  {q}
                </button>
              )
            })}
          </div>
        )}

        {/* Audio Track Chips */}
        {availableAudioTracks.length > 0 && (
          <div className="flex items-center flex-wrap gap-1.5">
            <span className="text-zinc-500 font-medium">صدا / زیرنویس:</span>
            {availableAudioTracks.map((a) => {
              const active = filters.audioTracks.includes(a)
              return (
                <button
                  key={a}
                  type="button"
                  onClick={() => toggleAudio(a)}
                  className={`px-2.5 py-1 rounded-lg border font-medium transition-colors ${
                    active
                      ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300'
                      : 'bg-zinc-800/60 border-zinc-700/60 text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  {a}
                </button>
              )
            })}
          </div>
        )}

        {/* Source Chips */}
        {availableSources.length > 1 && (
          <div className="flex items-center flex-wrap gap-1.5">
            <span className="text-zinc-500 font-medium">منبع:</span>
            {availableSources.map((s) => {
              const active = filters.sources.includes(s.id)
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => toggleSource(s.id)}
                  className={`px-2.5 py-1 rounded-lg border font-medium transition-colors ${
                    active
                      ? 'bg-violet-500/20 border-violet-500/50 text-violet-300'
                      : 'bg-zinc-800/60 border-zinc-700/60 text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  {s.name}
                </button>
              )
            })}
          </div>
        )}

        {/* Access Tier Chips — movies only */}
        {showMovieFilters && (
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
        )}

        {/* Censorship Chips — movies only */}
        {showMovieFilters && (
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
        )}
      </div>
    </div>
  )
}
