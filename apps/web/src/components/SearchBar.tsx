'use client'

import React, { useRef, useState, useEffect } from 'react'
import type { Category } from '@/types/media'
import { Search, RotateCw, X, Clock, Download, Layers } from 'lucide-react'
import { getRecentSearches, clearRecentSearches } from '@/lib/history'
import type { SourceScopeFilter } from '@/lib/urlFilters'

interface SearchBarProps {
  query: string
  category: Category
  isLoading: boolean
  onQueryChange: (q: string) => void
  onSearch: (
    q: string,
    refresh?: boolean,
    excludeSources?: string[],
    scope?: SourceScopeFilter
  ) => void
  inputRef?: React.RefObject<HTMLInputElement | null>
  /** FR-005: 'downloads' (default) hides streaming platforms; 'all' includes them. */
  scope?: SourceScopeFilter
  onScopeChange?: (scope: SourceScopeFilter) => void
}

const CATEGORIES: { id: Category; label: string }[] = [
  { id: 'movies', label: 'فیلم و سریال' },
  { id: 'games', label: 'بازی‌ها' },
  { id: 'music', label: 'موسیقی' },
]

export function SearchBar({
  query,
  category,
  isLoading,
  onQueryChange,
  onSearch,
  inputRef,
  scope = 'downloads',
  onScopeChange,
}: SearchBarProps) {
  const localInputRef = useRef<HTMLInputElement>(null)
  const activeInput = inputRef || localInputRef
  const [history, setHistory] = useState<string[]>([])
  const [isFocused, setIsFocused] = useState(false)

  useEffect(() => {
    setHistory(getRecentSearches(category))
  }, [category])

  function setScope(next: SourceScopeFilter) {
    if (next === scope) return
    onScopeChange?.(next)
    // Re-run immediately: the toggle is a filter on the current query, not a
    // preference to apply on the next search.
    if (query.trim()) onSearch(query.trim(), undefined, undefined, next)
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    onSearch(query.trim())
    setHistory(getRecentSearches(category))
  }

  function handleRefresh() {
    if (!query.trim()) return
    onSearch(query.trim(), true)
  }

  function handleSelectHistory(item: string) {
    onQueryChange(item)
    onSearch(item)
    setHistory(getRecentSearches(category))
  }

  function handleClearHistory() {
    clearRecentSearches(category)
    setHistory([])
  }

  return (
    <div className="w-full flex flex-col items-center gap-3">
      {/* FR-005 source scope */}
      {category === 'movies' && onScopeChange && (
        <div
          role="radiogroup"
          aria-label="دامنه منابع فیلم و سریال"
          className="seg"
        >
          {(
            [
              { id: 'downloads' as const, label: 'فقط دانلود', icon: Download },
              { id: 'all' as const, label: 'همه منابع', icon: Layers },
            ]
          ).map((opt) => {
            const Icon = opt.icon
            const isActive = scope === opt.id
            return (
              <button
                key={opt.id}
                type="button"
                role="radio"
                aria-checked={isActive}
                onClick={() => setScope(opt.id)}
                title={
                  opt.id === 'downloads'
                    ? 'فقط منابعی که لینک دانلود عمومی دارند'
                    : 'شامل پلتفرم‌های استریم (تماشای آنلاین)'
                }
                className="flex items-center gap-1.5"
                aria-pressed={isActive}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{opt.label}</span>
              </button>
            )
          })}
        </div>
      )}

      {/* Main Search Input Form */}
      <form
        role="search"
        onSubmit={handleSubmit}
        className="searchbar w-full"
      >
        <span className="icon">
          <Search className="w-4 h-4" />
        </span>

        <input
          ref={activeInput}
          type="search"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setTimeout(() => setIsFocused(false), 200)}
          placeholder={`جستجوی عنوان در بخش ${CATEGORIES.find((c) => c.id === category)?.label}...`}
          disabled={isLoading}
          aria-label="متن جستجو"
        />

        {/* Clear Button */}
        {query && !isLoading && (
          <button
            type="button"
            onClick={() => onQueryChange('')}
            className="iconbtn"
            style={{ width: '32px', height: '32px' }}
            aria-label="پاک کردن متن جستجو"
          >
            <X className="w-4 h-4" />
          </button>
        )}

        {/* Action Buttons: Force Refresh & Submit */}
        <div className="flex items-center gap-1.5">
          {query.trim().length > 0 && !isLoading && (
            <button
              type="button"
              onClick={handleRefresh}
              disabled={isLoading}
              title="تازه‌سازی و دریافت مجدد از وب‌سایت‌ها"
              aria-label="تازه‌سازی نتایج"
              className="iconbtn"
              style={{ width: '36px', height: '36px', background: 'transparent', color: 'var(--muted)', border: '1px solid var(--border)' }}
            >
              <RotateCw className="w-3.5 h-3.5" />
            </button>
          )}

          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="btn btn-primary"
          >
            {isLoading ? (
              <>
                <RotateCw className="w-3.5 h-3.5 animate-spin shrink-0" />
                <span>در حال جستجو...</span>
              </>
            ) : (
              <span>جستجو</span>
            )}
          </button>
        </div>
      </form>

      {/* Recent Searches Chips */}
      {history.length > 0 && (
        <div className="chips w-full justify-between" style={{ padding: '0 4px' }}>
          <div className="flex items-center gap-1.5 flex-wrap">
            <Clock className="w-3.5 h-3.5 text-zinc-500" />
            <span style={{ color: 'var(--muted-2)' }}>جستجوهای اخیر:</span>
            {history.map((item, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSelectHistory(item)}
                className="chip"
                style={{ minHeight: '30px' }}
              >
                {item}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={handleClearHistory}
            className="btn btn-quiet btn-sm"
          >
            پاک کردن تاریخچه
          </button>
        </div>
      )}
    </div>
  )
}
