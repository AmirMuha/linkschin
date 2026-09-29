'use client'

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import type { Category, MediaItem, SourceStatus } from '@/types/media'
import { searchMedia, fetchSources } from '@/lib/api'
import { addRecentSearch } from '@/lib/history'
import { SearchBar } from '@/components/SearchBar'
import { SourceStatusBar } from '@/components/SourceStatusBar'
import { InViewFilterBar, type FilterState } from '@/components/InViewFilterBar'
import { SkeletonGrid } from '@/components/ui/SkeletonGrid'
import { MovieCard } from '@/components/cards/MovieCard'
import { GameCard } from '@/components/cards/GameCard'
import { MusicCard } from '@/components/cards/MusicCard'
import { VideoPlayerModal } from '@/components/player/VideoPlayerModal'
import { GlobalAudioPlayer } from '@/components/player/GlobalAudioPlayer'
import { AudioPlayerProvider } from '@/context/AudioPlayerContext'
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts'
import { Sparkles, AlertCircle, Compass } from 'lucide-react'

export default function Home() {
  const [category, setCategory] = useState<Category>('movies')
  const [query, setQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [items, setItems] = useState<MediaItem[]>([])
  const [warnings, setWarnings] = useState<string[]>([])
  const [sources, setSources] = useState<SourceStatus[]>([])
  const [hasSearched, setHasSearched] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // In-view filter state
  const [filters, setFilters] = useState<FilterState>({
    qualities: [],
    audioTracks: [],
    sources: [],
  })

  // Video modal state
  const [videoModal, setVideoModal] = useState<{
    isOpen: boolean
    url: string | null
    title: string
  }>({
    isOpen: false,
    url: null,
    title: '',
  })

  const searchInputRef = useRef<HTMLInputElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Load registered sources on mount
  useEffect(() => {
    let mounted = true
    fetchSources()
      .then((data) => {
        if (mounted) setSources(data)
      })
      .catch(() => {
        // Fallback gracefully if API is waking up
      })
    return () => {
      mounted = false
    }
  }, [])

  // Keyboard shortcut handlers
  useKeyboardShortcuts({
    onSearchFocus: () => {
      searchInputRef.current?.focus()
      searchInputRef.current?.select()
    },
    onEscape: () => {
      searchInputRef.current?.blur()
      setVideoModal((prev) => ({ ...prev, isOpen: false }))
    },
  })

  // Execute search
  const handleSearch = useCallback(
    async (searchQuery: string, refresh = false) => {
      const q = searchQuery.trim()
      if (!q) return

      // Abort previous in-flight search
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
      const controller = new AbortController()
      abortControllerRef.current = controller

      setIsLoading(true)
      setErrorMessage(null)
      setHasSearched(true)

      // Reset filters on new search
      setFilters({ qualities: [], audioTracks: [], sources: [] })

      try {
        const response = await searchMedia(
          { q, category, refresh },
          controller.signal
        )
        setItems(response.items || [])
        setWarnings(response.warnings || [])
        addRecentSearch(q)
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') {
          return // User cancelled via new request
        }
        setErrorMessage(
          err instanceof Error
            ? err.message
            : 'خطایی در دریافت نتایج رخ داد. لطفاً مجدداً تلاش کنید.'
        )
        setItems([])
      } finally {
        setIsLoading(false)
      }
    },
    [category]
  )

  // Handle category switch
  function handleCategoryChange(newCategory: Category) {
    if (newCategory === category) return
    setCategory(newCategory)
    setItems([])
    setWarnings([])
    setHasSearched(false)
    setErrorMessage(null)
    setFilters({ qualities: [], audioTracks: [], sources: [] })

    // If query already entered, immediately execute search in new category
    if (query.trim()) {
      setTimeout(() => {
        handleSearch(query.trim())
      }, 0)
    }
  }

  // Derive available filter options from current items
  const availableFilterOptions = useMemo(() => {
    const qualitiesSet = new Set<string>()
    const audioSet = new Set<string>()
    const sourcesMap = new Map<string, string>()

    for (const item of items) {
      if (item.source_id) {
        sourcesMap.set(item.source_id, item.source_id)
      }
      for (const variant of item.movie_variants || []) {
        if (variant.quality) qualitiesSet.add(variant.quality)
        if (variant.audio_track) audioSet.add(variant.audio_track)
      }
    }

    return {
      qualities: Array.from(qualitiesSet).sort(),
      audioTracks: Array.from(audioSet).sort(),
      sources: Array.from(sourcesMap.entries()).map(([id, name]) => ({
        id,
        name,
      })),
    }
  }, [items])

  // In-memory filtered items
  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      // Source filter
      if (
        filters.sources.length > 0 &&
        !filters.sources.includes(item.source_id)
      ) {
        return false
      }

      // Quality filter (movies)
      if (filters.qualities.length > 0) {
        const hasQuality = item.movie_variants?.some((v) =>
          filters.qualities.includes(v.quality)
        )
        if (!hasQuality) return false
      }

      // Audio track filter (movies)
      if (filters.audioTracks.length > 0) {
        const hasAudio = item.movie_variants?.some((v) =>
          filters.audioTracks.includes(v.audio_track)
        )
        if (!hasAudio) return false
      }

      return true
    })
  }, [items, filters])

  function handleOpenVideo(url: string, title: string) {
    setVideoModal({
      isOpen: true,
      url,
      title,
    })
  }

  return (
    <AudioPlayerProvider>
      <div className="min-h-screen flex flex-col justify-between pb-24">
        {/* Top Header */}
        <header className="w-full border-b border-zinc-900 bg-zinc-950/70 backdrop-blur-xl sticky top-0 z-30 py-2.5 px-4 sm:px-6">
          <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-[0_0_12px_rgba(6,182,212,0.2)]">
                <Sparkles className="w-4 h-4" />
              </div>
              <span className="font-bold text-sm tracking-tight text-zinc-100">
                MovieFetcher
              </span>
            </div>

            <div>
              <SourceStatusBar sources={sources} warnings={warnings} />
            </div>
          </div>
        </header>

        {/* Hero & Search Section */}
        <main className="w-full max-w-7xl mx-auto px-4 sm:px-6 py-4 sm:py-6 flex flex-col items-center gap-5 flex-1">
          {/* Compact Welcome Title (Only shown when not searched) */}
          {!hasSearched && items.length === 0 && (
            <div className="text-center flex flex-col items-center gap-1.5 max-w-xl pt-2 animate-in fade-in">
              <h1 className="text-lg sm:text-2xl font-bold text-zinc-100">
                دسترسی مستقیم به فایل‌های فیلم، بازی و موسیقی
              </h1>
              <p className="text-xs text-zinc-400 leading-relaxed">
                استخراج لحظه‌ای لینک‌های CDN بدون تبلیغات پاپ‌آپ، ریدایرکت یا واسطه
              </p>
            </div>
          )}

          {/* SearchBar */}
          <SearchBar
            query={query}
            category={category}
            isLoading={isLoading}
            onQueryChange={setQuery}
            onCategoryChange={handleCategoryChange}
            onSearch={(q, refresh) => handleSearch(q, refresh)}
            inputRef={searchInputRef}
          />

          {/* Filter Bar */}
          {items.length > 0 && !isLoading && (
            <div className="w-full max-w-5xl">
              <InViewFilterBar
                availableQualities={availableFilterOptions.qualities}
                availableAudioTracks={availableFilterOptions.audioTracks}
                availableSources={availableFilterOptions.sources}
                filters={filters}
                onFilterChange={setFilters}
              />
            </div>
          )}

          {/* Content States */}
          {isLoading && (
            <div className="w-full max-w-7xl pt-4">
              <SkeletonGrid count={8} />
            </div>
          )}

          {errorMessage && !isLoading && (
            <div
              role="alert"
              className="w-full max-w-xl p-6 rounded-3xl bg-rose-500/10 border border-rose-500/30 text-rose-300 flex flex-col items-center text-center gap-3 mt-6 shadow-2xl"
            >
              <AlertCircle className="w-10 h-10 text-rose-400" />
              <h3 className="font-bold text-base">خطا در دریافت اطلاعات</h3>
              <p className="text-xs text-rose-300/90 leading-relaxed">
                {errorMessage}
              </p>
              <button
                type="button"
                onClick={() => handleSearch(query, true)}
                className="mt-2 px-4 py-2 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 text-xs font-semibold transition-colors"
              >
                تلاش مجدد با دور زدن کش
              </button>
            </div>
          )}

          {!isLoading && !errorMessage && hasSearched && items.length === 0 && (
            <div className="w-full max-w-md p-8 rounded-3xl bg-zinc-900/40 border border-zinc-800 text-center flex flex-col items-center gap-3 mt-8">
              <Compass className="w-12 h-12 text-zinc-600" />
              <h3 className="font-bold text-base text-zinc-200">
                موردی یافت نشد
              </h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                عنوانی با مشخصات «{query}» در پایگاه‌ها پیدا نشد. املای کلمه را بررسی کرده یا نام انگلیسی/فارسی آن را جستجو کنید.
              </p>
            </div>
          )}

          {!isLoading && !errorMessage && filteredItems.length > 0 && (
            <div className="w-full grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 pt-2">
              {filteredItems.map((item) => {
                if (item.category === 'movies') {
                  return (
                    <MovieCard
                      key={item.id}
                      item={item}
                      onPlayStream={handleOpenVideo}
                    />
                  )
                }
                if (item.category === 'games') {
                  return <GameCard key={item.id} item={item} />
                }
                if (item.category === 'music') {
                  return <MusicCard key={item.id} item={item} />
                }
                return null
              })}
            </div>
          )}
        </main>

        {/* Global Video Modal */}
        <VideoPlayerModal
          isOpen={videoModal.isOpen}
          streamUrl={videoModal.url}
          title={videoModal.title}
          onClose={() => setVideoModal((prev) => ({ ...prev, isOpen: false }))}
        />

        {/* Global Audio Player Bar */}
        <GlobalAudioPlayer />
      </div>
    </AudioPlayerProvider>
  )
}
