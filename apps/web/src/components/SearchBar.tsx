'use client'

import React, { useRef, useState, useEffect } from 'react'
import type { Category } from '@/types/media'
import { Search, RotateCw, X, Film, Gamepad2, Music, Clock } from 'lucide-react'
import { getRecentSearches, clearRecentSearches } from '@/lib/history'

interface SearchBarProps {
  query: string
  category: Category
  isLoading: boolean
  onQueryChange: (q: string) => void
  onCategoryChange: (cat: Category) => void
  onSearch: (q: string, refresh?: boolean, excludeSources?: string[]) => void
  inputRef?: React.RefObject<HTMLInputElement | null>
}

const CATEGORIES: { id: Category; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: 'movies', label: 'فیلم و سریال', icon: Film },
  { id: 'games', label: 'بازی‌ها', icon: Gamepad2 },
  { id: 'music', label: 'موسیقی', icon: Music },
]

export function SearchBar({
  query,
  category,
  isLoading,
  onQueryChange,
  onCategoryChange,
  onSearch,
  inputRef,
}: SearchBarProps) {
  const localInputRef = useRef<HTMLInputElement>(null)
  const activeInput = inputRef || localInputRef
  const [history, setHistory] = useState<string[]>([])
  const [isFocused, setIsFocused] = useState(false)

  useEffect(() => {
    setHistory(getRecentSearches())
  }, [])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    onSearch(query.trim())
    setHistory(getRecentSearches())
  }

  function handleRefresh() {
    if (!query.trim()) return
    onSearch(query.trim(), true)
  }

  function handleSelectHistory(item: string) {
    onQueryChange(item)
    onSearch(item)
    setHistory(getRecentSearches())
  }

  function handleClearHistory() {
    clearRecentSearches()
    setHistory([])
  }

  return (
    <div className="w-full flex flex-col items-center gap-3 max-w-3xl mx-auto">
      {/* Category Tabs */}
      <div
        role="tablist"
        aria-label="دسته‌بندی‌های رسانه"
        className="flex items-center p-1 rounded-2xl bg-zinc-900/90 border border-zinc-800 shadow-xl backdrop-blur-md"
      >
        {CATEGORIES.map((cat) => {
          const Icon = cat.icon
          const isActive = category === cat.id
          return (
            <button
              key={cat.id}
              role="tab"
              aria-selected={isActive}
              type="button"
              onClick={() => onCategoryChange(cat.id)}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-medium transition-all ${
                isActive
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 shadow-[0_0_12px_rgba(6,182,212,0.25)]'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50 border border-transparent'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{cat.label}</span>
            </button>
          )
        })}
      </div>

      {/* Main Search Input Form */}
      <form
        role="search"
        onSubmit={handleSubmit}
        className="w-full relative flex items-center shadow-xl rounded-2xl bg-zinc-900/90 border border-zinc-700/80 focus-within:border-cyan-500 focus-within:ring-2 focus-within:ring-cyan-500/30 transition-all backdrop-blur-md"
      >
        <div className="ps-3.5 text-zinc-400 flex items-center pointer-events-none">
          <Search className="w-4 h-4 text-cyan-400" />
        </div>

        <input
          ref={activeInput}
          type="text"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setTimeout(() => setIsFocused(false), 200)}
          placeholder={`جستجوی عنوان در بخش ${CATEGORIES.find((c) => c.id === category)?.label}...`}
          disabled={isLoading}
          aria-label="متن جستجو"
          className="w-full min-w-0 bg-transparent px-3 py-3 text-sm sm:text-base text-zinc-100 placeholder:text-zinc-500 focus:outline-none"
        />

        {/* Clear Button */}
        {query && !isLoading && (
          <button
            type="button"
            onClick={() => onQueryChange('')}
            className="p-1.5 text-zinc-400 hover:text-zinc-200 transition-colors shrink-0"
            aria-label="پاک کردن متن جستجو"
          >
            <X className="w-4 h-4" />
          </button>
        )}

        {/* Keyboard shortcut hint */}
        {!query && (
          <div className="hidden sm:flex items-center pe-3 pointer-events-none shrink-0">
            <kbd className="px-1.5 py-0.5 text-2xs font-mono font-semibold text-zinc-400 bg-zinc-800 border border-zinc-700 rounded-md">
              /
            </kbd>
          </div>
        )}

        {/* Action Buttons: Force Refresh & Submit */}
        <div className="flex items-center gap-1.5 pe-1.5 shrink-0">
          {query.trim().length > 0 && !isLoading && (
            <button
              type="button"
              onClick={handleRefresh}
              disabled={isLoading}
              title="تازه‌سازی و دریافت مجدد از وب‌سایت‌ها"
              aria-label="تازه‌سازی نتایج"
              className="p-2 rounded-xl text-zinc-400 hover:text-cyan-400 hover:bg-zinc-800/80 transition-colors shrink-0"
            >
              <RotateCw className="w-3.5 h-3.5" />
            </button>
          )}

          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="shrink-0 whitespace-nowrap min-w-[85px] px-4 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs sm:text-sm transition-all disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-1.5 shadow-[0_0_12px_rgba(6,182,212,0.25)]"
          >
            {isLoading ? (
              <>
                <RotateCw className="w-3.5 h-3.5 animate-spin shrink-0" />
                <span className="whitespace-nowrap">در حال جستجو...</span>
              </>
            ) : (
              <span className="whitespace-nowrap">جستجو</span>
            )}
          </button>
        </div>
      </form>

      {/* Recent Searches Chips */}
      {history.length > 0 && (
        <div className="w-full flex items-center justify-between flex-wrap gap-2 text-xs text-zinc-400 px-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <Clock className="w-3.5 h-3.5 text-zinc-500" />
            <span className="text-zinc-500">جستجوهای اخیر:</span>
            {history.map((item, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSelectHistory(item)}
                className="px-2.5 py-1 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-zinc-700 hover:text-zinc-200 transition-colors"
              >
                {item}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={handleClearHistory}
            className="text-zinc-500 hover:text-rose-400 transition-colors text-xs"
          >
            پاک کردن تاریخچه
          </button>
        </div>
      )}
    </div>
  )
}
