'use client'

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import type { Category, MediaItem, SourceStatus } from '@/types/media'
import { searchMedia, fetchSources, fetchTrending, fetchLatest } from '@/lib/api'
import { addRecentSearch } from '@/lib/history'
import { SearchBar } from '@/components/SearchBar'
import { SourceStatusBar } from '@/components/SourceStatusBar'
import { InViewFilterBar, EMPTY_FILTERS, type FilterState } from '@/components/InViewFilterBar'
import { Header } from '@/components/Header'
import { HeroBanner } from '@/components/HeroBanner'
import { StaticSections } from '@/components/StaticSections'
import { DetailDrawer } from '@/components/DetailDrawer'
import { AiAssistant } from '@/components/AiAssistant'
import { Footer } from '@/components/Footer'
import type { CatalogItem } from '@/lib/catalog'
import {
  itemMatchesAlbums,
  itemMatchesArtists,
  itemMatchesBitrates,
  itemMatchesCensorship,
  itemMatchesTier,
} from '@/lib/filters'
import {
  buildSearchParams,
  parseCensorshipParam,
  parseScopeParam,
  parseTierParam,
  type SourceScopeFilter,
} from '@/lib/urlFilters'
import { SkeletonGrid } from '@/components/ui/SkeletonGrid'
import { MovieCard } from '@/components/cards/MovieCard'
import { GameCard } from '@/components/cards/GameCard'
import { MusicCard } from '@/components/cards/MusicCard'
import { VideoPlayerModal } from '@/components/player/VideoPlayerModal'
import { GlobalAudioPlayer } from '@/components/player/GlobalAudioPlayer'
import { AudioPlayerProvider } from '@/context/AudioPlayerContext'
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts'
import { useFavorites } from '@/hooks/useFavorites'
import { AlertCircle, Compass } from 'lucide-react'

const HIDDEN_SOURCES_KEY = 'mf:hiddenSources'

interface MediaCategoryPageProps {
  category: Category
}

export function MediaCategoryPage({ category }: MediaCategoryPageProps) {
  const [query, setQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [items, setItems] = useState<MediaItem[]>([])
  const [warnings, setWarnings] = useState<string[]>([])
  const [sources, setSources] = useState<SourceStatus[]>([])
  const [hasSearched, setHasSearched] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  // FR-005: downloads-only by default; 'all' opts into subscription sources.
  const [scope, setScope] = useState<SourceScopeFilter>('downloads')

  // In-view filter state. `hiddenSources` is the per-user hidden set: it is
  // persisted to localStorage and re-sent on every search, never to the server.
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS)

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

  // Design system drawer and assistant states
  const [selectedCatalogItem, setSelectedCatalogItem] = useState<CatalogItem | null>(null)
  const [aiOpen, setAiOpen] = useState(false)
  const favorites = useFavorites()
  const [dynamicTrending, setDynamicTrending] = useState<any[]>([])
  const [dynamicLatest, setDynamicLatest] = useState<any[]>([])

  // Fetch live trending and latest items dynamically from catalog API
  useEffect(() => {
    let ignore = false
    fetchTrending(category, 12).then((res) => {
      if (!ignore && res && res.length > 0) setDynamicTrending(res)
    })
    fetchLatest(category, 14).then((res) => {
      if (!ignore && res && res.length > 0) setDynamicLatest(res)
    })
    return () => {
      ignore = true
    }
  }, [category])

  // Sync category to body dataset for CSS variables
  useEffect(() => {
    document.body.dataset.cat = category
  }, [category])

  const searchInputRef = useRef<HTMLInputElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Load registered sources on mount and poll every 30s
  useEffect(() => {
    let mounted = true
    const load = () => {
      fetchSources()
        .then((data) => {
          if (mounted) setSources(data)
        })
        .catch(() => {
          // Fallback gracefully if API is waking up
        })
    }

    load()
    const timer = setInterval(load, 30000)

    return () => {
      mounted = false
      clearInterval(timer)
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

  // Restore the saved hidden set after hydration (client-only, no server state).
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(HIDDEN_SOURCES_KEY)
      if (!raw) return
      const parsed: unknown = JSON.parse(raw)
      if (Array.isArray(parsed)) {
        const ids = parsed.filter((v): v is string => typeof v === 'string')
        if (ids.length > 0) setFilters((prev) => ({ ...prev, hiddenSources: ids }))
      }
    } catch {
      // A corrupt saved set must never break the app; start from the default set.
    }
  }, [])

  // Persist the hidden set and re-run the current query so the exclusion takes
  // effect server-side (the filter can only ever remove sources).
  useEffect(() => {
    try {
      window.localStorage.setItem(HIDDEN_SOURCES_KEY, JSON.stringify(filters.hiddenSources))
    } catch {
      // Storage unavailable (private mode/quota) — the toggle still works in-session.
    }
  }, [filters.hiddenSources])

  // Execute search
  const handleSearch = useCallback(
    async (
      searchQuery: string,
      refresh = false,
      excludeSources?: string[],
      requestScope?: SourceScopeFilter
    ) => {
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
      setQuery(q)

      // Put the query in the URL so a refresh or a shared link replays it (FR-012).
      const urlParams = new URLSearchParams(window.location.search)
      urlParams.set('q', q)
      window.history.replaceState(
        null,
        '',
        `${window.location.pathname}?${urlParams.toString()}`
      )

      // Reset in-view filters on new search. The hidden set is NOT reset — it is
      // a durable per-user preference, not a per-search filter.
      setFilters((prev) => ({ ...EMPTY_FILTERS, hiddenSources: prev.hiddenSources }))

      try {
        const response = await searchMedia(
          { q, category, refresh, excludeSources, scope: requestScope ?? scope },
          controller.signal
        )
        setItems(response.items || [])
        setWarnings(response.warnings || [])
        addRecentSearch(q, category)

        // Sync sources immediately after search, as backend health state may have changed
        fetchSources().then((data) => setSources(data)).catch(() => {})
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') {
          return // User cancelled via new request
        }
        setErrorMessage(
          err instanceof Error
            ? err.message
            : 'ارتباط با سرور برقرار نشد. لطفا اتصال اینترنت خود را بررسی کنید.'
        )
        setItems([])
      } finally {
        setIsLoading(false)
      }
    },
    [category, scope]
  )

  // Open video modal
  function handleOpenVideo(url: string, title: string) {
    setVideoModal({
      isOpen: true,
      url,
      title,
    })
  }

  // Derive distinct filter options from current items
  const filterOptions = useMemo(() => {
    const qualitiesSet = new Set<string>()
    const audioSet = new Set<string>()
    const artistsSet = new Set<string>()
    const albumsSet = new Set<string>()
    const bitratesSet = new Set<string>()
    const sourcesMap = new Map<string, string>()

    for (const item of items) {
      if (item.source_id) {
        sourcesMap.set(item.source_id, item.source_id)
      }
      for (const variant of item.movie_variants || []) {
        if (variant.quality) qualitiesSet.add(variant.quality)
        if (variant.audio_track) audioSet.add(variant.audio_track)
      }
      for (const track of item.music_tracks || []) {
        if (track.artist) artistsSet.add(track.artist)
        if (track.album) albumsSet.add(track.album)
        for (const dl of track.downloads || []) {
          if (dl.bitrate) bitratesSet.add(dl.bitrate)
        }
      }
    }

    return {
      qualities: Array.from(qualitiesSet).sort(),
      audioTracks: Array.from(audioSet).sort(),
      artists: Array.from(artistsSet).sort((a, b) => a.localeCompare(b, 'fa')),
      albums: Array.from(albumsSet).sort((a, b) => a.localeCompare(b, 'fa')),
      bitrates: Array.from(bitratesSet).sort(),
      sources: Array.from(sourcesMap.entries()).map(([id, name]) => ({
        id,
        name,
      })),
    }
  }, [items])

  // In-memory filtered items
  const filteredItems = useMemo(() => {
    const hiddenSources = filters.hiddenSources
    return items.filter((item) => {
      // Hidden-source set: applied server-side via `sources=` on the next search
      // and here too, so the toggle takes effect without a refetch.
      if (hiddenSources.length > 0 && hiddenSources.includes(item.source_id)) {
        return false
      }

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

      // Artist / album / bitrate filters (music)
      if (!itemMatchesArtists(item, filters.artists)) return false
      if (!itemMatchesAlbums(item, filters.albums)) return false
      if (!itemMatchesBitrates(item, filters.bitrates)) return false

      // Source access tier + censorship (spec 007). Freemium items stay visible under
      // either tier; only their download rows are pruned inside MovieDownloadMatrix.
      if (!itemMatchesTier(item, filters.accessTier)) return false
      if (!itemMatchesCensorship(item, filters.censorship)) return false

      return true
    })
  }, [items, filters])

  // Seed tier/censorship from the URL once on mount so a shared or refreshed link
  // restores the same filtered view (FR-012). The query string is restored too, so a
  // reload replays the search instead of landing on an empty grid.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const tier = parseTierParam(params.get('tier'))
    const censorship = parseCensorshipParam(params.get('censorship'))
    const initialScope = parseScopeParam(params.get('scope'))
    const initialQuery = params.get('q')
    // Seeded before the replay search so handleSearch reads the shared scope rather
    // than the default; setScope is async, so the value is passed explicitly too.
    if (initialScope !== 'downloads') setScope(initialScope)
    if (initialQuery) {
      setQuery(initialQuery)
      handleSearch(initialQuery, false, undefined, initialScope)
    }
    // Applied after handleSearch, which resets filters for a fresh query.
    if (tier !== 'all' || censorship !== 'all') {
      setFilters((prev) => ({ ...prev, accessTier: tier, censorship }))
    }
    // Runs once on mount; handleSearch is stable enough for this replay.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Mirror filter changes back to the URL without navigating (FR-011, FR-012).
  useEffect(() => {
    const params = buildSearchParams(
      filters.accessTier,
      filters.censorship,
      new URLSearchParams(window.location.search),
      scope
    )
    const next = `${window.location.pathname}${params.toString() ? `?${params}` : ''}`
    window.history.replaceState(null, '', next)
  }, [filters.accessTier, filters.censorship, scope])

  return (
    <AudioPlayerProvider>
      <div className="pb-24" data-cat={category}>
        {/* Header */}
        <Header
          activePage={category}
          category={category}
          onOpenAi={() => setAiOpen(true)}
          rightSlot={
            <SourceStatusBar
              sources={sources}
              hiddenSources={filters.hiddenSources}
              onToggleHidden={(id) =>
                setFilters((prev) => {
                  const exists = prev.hiddenSources.includes(id)
                  const next = exists
                    ? prev.hiddenSources.filter((s) => s !== id)
                    : [...prev.hiddenSources, id]
                  return { ...prev, hiddenSources: next }
                })
              }
              onRestoreAllSources={() =>
                setFilters((prev) => ({ ...EMPTY_FILTERS, hiddenSources: prev.hiddenSources }))
              }
            />
          }
        />

        {/* Main Content */}
        <main id="main">
          {/* Hero Banner (Shown when idle / not searched) */}
          {!hasSearched && items.length === 0 && (
            <HeroBanner
              category={category}
              onOpenDetails={setSelectedCatalogItem}
              onToggleFavorite={favorites.toggle}
              isItemFavorite={favorites.isLiked}
            />
          )}

          {/* SearchBar */}
          <section className="wrap" data-od-id="search-section" style={{ marginTop: '22px' }}>
            <SearchBar
              query={query}
              category={category}
              isLoading={isLoading}
              onQueryChange={setQuery}
              onSearch={(q, refresh, excludeSources, requestScope) =>
                handleSearch(q, refresh, filters.hiddenSources, requestScope)
              }
              inputRef={searchInputRef}
              scope={scope}
              onScopeChange={setScope}
            />
          </section>

          {/* Filter Bar (When items exist) */}
          {items.length > 0 && !isLoading && (
            <div className="wrap" style={{ marginTop: '16px' }}>
              <InViewFilterBar
                category={category}
                availableQualities={filterOptions.qualities}
                availableAudioTracks={filterOptions.audioTracks}
                availableArtists={filterOptions.artists}
                availableAlbums={filterOptions.albums}
                availableBitrates={filterOptions.bitrates}
                availableSources={filterOptions.sources}
                filters={filters}
                onFilterChange={setFilters}
              />
            </div>
          )}

          {/* Loading Skeleton */}
          {isLoading && (
            <div className="wrap" style={{ marginTop: '20px' }}>
              <SkeletonGrid count={8} />
            </div>
          )}

          {/* Error Message */}
          {errorMessage && !isLoading && (
            <div className="wrap" style={{ marginTop: '20px' }}>
              <div
                role="alert"
                className="w-full max-w-xl mx-auto p-6 rounded-3xl bg-rose-500/10 border border-rose-500/30 text-rose-300 flex flex-col items-center text-center gap-3 shadow-2xl"
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
            </div>
          )}

          {/* Empty Results State */}
          {!isLoading && !errorMessage && hasSearched && filteredItems.length === 0 && (
            <div className="wrap">
              <div className="empty" style={{ marginTop: '24px' }}>
                <Compass className="w-12 h-12 text-zinc-600" />
                <strong>
                  {items.length === 0
                    ? 'موردی یافت نشد'
                    : filters.hiddenSources.length > 0
                      ? 'همه نتایج پنهان شده‌اند'
                      : 'نتیجه‌ای با این فیلترها نیست'}
                </strong>
                <span>
                  {items.length === 0
                    ? `عنوانی با مشخصات «${query}» در پایگاه‌ها پیدا نشد. املای کلمه را بررسی کرده یا نام انگلیسی/فارسی آن را جستجو کنید.`
                    : filters.hiddenSources.length > 0
                      ? `${filters.hiddenSources.length} منبع در فهرست منابع بالا پنهان شده و همه نتایج از آن‌هاست. از آیکن چشم آن‌ها را دوباره نشان دهید.`
                      : 'فیلترهای انتخاب‌شده هیچ‌کدام از نتایج را پوشش نمی‌دهند. فیلترها را کم یا حذف کنید.'}
                </span>
                {items.length > 0 && filters.hiddenSources.length === 0 && (
                  <button
                    type="button"
                    onClick={() =>
                      setFilters((prev) => ({
                        ...EMPTY_FILTERS,
                        hiddenSources: prev.hiddenSources,
                      }))
                    }
                    className="btn btn-ghost mt-2"
                  >
                    حذف تمام فیلترها
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Search Results Grid */}
          {!isLoading && !errorMessage && filteredItems.length > 0 && (
            <section className="wrap sec" data-od-id="section-results">
              <div className="sec-head">
                <h2>نتایج جستجو</h2>
                <span className="sub">{filteredItems.length} مورد پیدا شد</span>
              </div>
              <div className="grid grid-6 pt-2">
                {filteredItems.map((item) => {
                  if (item.category === 'movies') {
                    return (
                      <MovieCard
                        key={item.id}
                        item={item}
                        onPlayStream={handleOpenVideo}
                        activeTierFilter={filters.accessTier}
                        activeCensorshipFilter={filters.censorship}
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
            </section>
          )}

          {/* Idle Homepage Sections (Health, Trending, Shelf, Why, FAQ) */}
          {!hasSearched && items.length === 0 && !isLoading && (
            <StaticSections
              category={category}
              onOpenDetails={setSelectedCatalogItem}
              onToggleFavorite={favorites.toggle}
              isItemFavorite={favorites.isLiked}
              dynamicTrending={dynamicTrending}
              dynamicLatest={dynamicLatest}
            />
          )}
        </main>

        {/* Catalog Item Detail Drawer */}
        <DetailDrawer
          item={selectedCatalogItem}
          isOpen={Boolean(selectedCatalogItem)}
          onClose={() => setSelectedCatalogItem(null)}
          onPlayStream={handleOpenVideo}
          onToggleFavorite={favorites.toggle}
          isItemFavorite={favorites.isLiked}
          persistenceBlocked={favorites.persistenceBlocked}
        />

        {/* AI Assistant */}
        <AiAssistant
          category={category}
          isOpen={aiOpen}
          onToggle={() => setAiOpen((prev) => !prev)}
          onClose={() => setAiOpen(false)}
        />

        {/* Global Video Modal */}
        <VideoPlayerModal
          isOpen={videoModal.isOpen}
          streamUrl={videoModal.url}
          title={videoModal.title}
          onClose={() => setVideoModal((prev) => ({ ...prev, isOpen: false }))}
        />

        {/* Global Audio Player Bar */}
        <GlobalAudioPlayer />

        {/* Site Footer */}
        <Footer />
      </div>
    </AudioPlayerProvider>
  )
}
