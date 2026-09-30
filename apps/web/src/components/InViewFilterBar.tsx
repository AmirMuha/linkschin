'use client'

import React from 'react'
import type { SourceStatus } from '@/types/media'
import { Filter, X, EyeOff, RotateCcw } from 'lucide-react'

export interface FilterState {
  qualities: string[]
  audioTracks: string[]
  sources: string[]
  /** Persisted per-user hidden set; sent as repeated `sources=` params. */
  hiddenSources: string[]
}

interface InViewFilterBarProps {
  availableQualities: string[]
  availableAudioTracks: string[]
  availableSources: { id: string; name: string }[]
  filters: FilterState
  onFilterChange: (filters: FilterState) => void
  /** Full registry, so hide toggles can show status and refuse degraded/inactive. */
  sourceRegistry?: SourceStatus[]
}

export function InViewFilterBar({
  availableQualities,
  availableAudioTracks,
  availableSources,
  filters,
  onFilterChange,
  sourceRegistry = [],
}: InViewFilterBarProps) {
  const hasActiveFilters =
    filters.qualities.length > 0 ||
    filters.audioTracks.length > 0 ||
    filters.sources.length > 0
  const hiddenSources = filters.hiddenSources ?? []
  const hasHiddenSources = hiddenSources.length > 0

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

  function toggleHidden(id: string) {
    const next = hiddenSources.includes(id)
      ? hiddenSources.filter((item) => item !== id)
      : [...hiddenSources, id]
    onFilterChange({ ...filters, hiddenSources: next })
  }

  function handleReset() {
    onFilterChange({
      qualities: [],
      audioTracks: [],
      sources: [],
      hiddenSources: [],
    })
  }

  // Only render if there are options to filter by
  if (
    availableQualities.length === 0 &&
    availableAudioTracks.length === 0 &&
    availableSources.length <= 1 &&
    sourceRegistry.length === 0
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
          {hasHiddenSources && (
            <button
              type="button"
              onClick={() => onFilterChange({ ...filters, hiddenSources: [] })}
              className="flex items-center gap-1 text-xs text-zinc-400 hover:text-cyan-400 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>بازگردانی همه منابع</span>
            </button>
          )}
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
      </div>

      {/* Per-source hide toggles (FR-029/FR-031). Real checkboxes: labelled,
          keyboard-operable, focus order follows visual order. A hidden source
          stays listed so it can be undone, and a source the system has marked
          degraded/inactive is not offered a hide control at all. */}
      {sourceRegistry.length > 0 && (
        <fieldset className="flex flex-col gap-2 pt-3 border-t border-zinc-800/80">
          <legend className="text-2xs font-semibold text-zinc-400 px-1">
            پنهان‌کردن منابع در نتایج بعدی
          </legend>

          <div className="flex flex-wrap gap-x-5 gap-y-2">
            {sourceRegistry.map((s) => {
              const status = s.status ?? (s.enabled ? 'active' : 'inactive')
              const blocked = status === 'degraded' || status === 'inactive'
              const hidden = hiddenSources.includes(s.id)

              if (blocked) {
                return (
                  <span
                    key={s.id}
                    className="flex items-center gap-1.5 text-2xs text-zinc-500"
                    title={s.inactive_reason ?? undefined}
                  >
                    <span className="text-zinc-400 font-medium">{s.name}</span>
                    <span>{status === 'degraded' ? 'افت کیفیت — قابل پنهان‌سازی نیست' : 'غیرفعال — قابل پنهان‌سازی نیست'}</span>
                  </span>
                )
              }

              return (
                <label
                  key={s.id}
                  className="flex items-center gap-1.5 text-2xs text-zinc-400 cursor-pointer hover:text-zinc-200 transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={hidden}
                    onChange={() => toggleHidden(s.id)}
                    className="w-3.5 h-3.5 accent-cyan-500 cursor-pointer"
                  />
                  <span className="flex items-center gap-1">
                    <span className={hidden ? 'line-through' : undefined}>{s.name}</span>
                    {s.kind === 'reference' && <span>ارجاعی</span>}
                    {hidden && <EyeOff className="w-3 h-3" aria-hidden="true" />}
                  </span>
                </label>
              )
            })}
          </div>
        </fieldset>
      )}
    </div>
  )
}
