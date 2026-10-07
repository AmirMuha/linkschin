'use client'

import React, { useState, useEffect } from 'react'
import type { Category, MediaItem } from '@/types/media'
import { toFaDigits } from '@/lib/format'
import { Download, Heart } from 'lucide-react'

interface HeroBannerProps {
  category: Category
  /** Fetched rows only — an empty shelf renders no hero at all. */
  items: MediaItem[]
  onOpenDetails: (item: MediaItem) => void
  onToggleFavorite: (item: MediaItem) => void
  isItemFavorite: (id: string) => boolean
}

const HERO_INTERVAL_MS = 6000
const REDUCED_MOTION = '(prefers-reduced-motion: reduce)'

export function HeroBanner({
  category,
  items,
  onOpenDetails,
  onToggleFavorite,
  isItemFavorite,
}: HeroBannerProps) {
  const [index, setIndex] = useState(0)
  // Pointer is resting on the rail or the dots — a click there is likely.
  const [paused, setPaused] = useState(false)
  // Tab is backgrounded; a timer that keeps firing there just wastes cycles.
  const [hidden, setHidden] = useState(false)
  // Bumped by manual navigation so the dwell restarts from a full interval
  // instead of stranding the viewer on a slide that advances a beat later.
  const [nav, setNav] = useState(0)

  // Reset index when category switches. Paused resets too: React never fires
  // onMouseLeave on unmount, and the pointer is still over the dots after the
  // swap, which would otherwise leave the hero frozen.
  useEffect(() => {
    setIndex(0)
    setPaused(false)
  }, [category, items])

  useEffect(() => {
    const onVisibility = () => setHidden(document.hidden)
    document.addEventListener('visibilitychange', onVisibility)
    return () => document.removeEventListener('visibilitychange', onVisibility)
  }, [])

  const list = items
  const count = list.length
  const isMusic = category === 'music'
  // Guarded rather than early-returned so the hook order below never shifts.
  const activeIndex = count ? index % count : 0

  useEffect(() => {
    if (paused || hidden || count < 2) return
    if (window.matchMedia(REDUCED_MOTION).matches) return
    const timer = setInterval(
      () => setIndex((i) => (i + 1) % count),
      HERO_INTERVAL_MS
    )
    return () => clearInterval(timer)
  }, [paused, hidden, count, nav])

  // Warm the next slide's art: a poster is often several hundred KB, so without
  // this the hero paints empty for a beat on every advance.
  const nextItem = list[(activeIndex + 1) % count]
  const nextSrc = nextItem?.poster_url ?? null

  useEffect(() => {
    if (nextSrc) new Image().src = nextSrc
  }, [nextSrc])

  if (count === 0) return null

  const it = list[activeIndex]
  const isSaved = isItemFavorite(it.id)

  const goTo = (n: number) => {
    setIndex(n)
    setNav((v) => v + 1)
  }

  const eyebrowText = isMusic
    ? 'آلبوم'
    : category === 'games'
      ? it.game_releases?.[0]?.release_group || 'بازی'
      : 'فیلم و سریال'

  const metaText = it.release_year ? toFaDigits(it.release_year) : ''

  const descText = it.description || ' '

  const titleText = (it.original_title || it.title).toUpperCase()

  return (
    <section className="wrap" data-od-id="hero-section" aria-label="اثر شاخص">
      <div className={`hero ${isMusic ? 'cover' : ''}`} id="hero">
        {it.poster_url ? (
          <img
            key={it.id}
            className="hero-shot"
            src={it.poster_url}
            alt={`تصویر شاخص ${it.title}`}
          />
        ) : (
          <div className="hero-shot" />
        )}

        <div
          className="hero-rail"
          id="heroRail"
          aria-label="اثرهای شاخص"
          onMouseEnter={() => setPaused(true)}
          onMouseLeave={() => setPaused(false)}
        >
          {list.map((item, n) => {
            const isCurrent = n === activeIndex
            return (
              <button
                key={item.id}
                type="button"
                className={item.music_tracks?.length ? 'sq' : ''}
                aria-current={isCurrent}
                aria-label={`نمایش ${item.title}`}
                onClick={() => goTo(n)}
              >
                {item.poster_url ? <img src={item.poster_url} alt="" loading="lazy" /> : null}
              </button>
            )
          })}
        </div>

        <div className="hero-body">
          <div className="eyebrow">
            <span className="pill-red" id="heroEyebrow">
              {eyebrowText}
            </span>
            {metaText ? (
              <span className="pill-ghost" id="heroMeta">
                {metaText}
              </span>
            ) : null}
          </div>

          <h1 id="heroTitle">{titleText}</h1>
          <p className="hero-desc" id="heroDesc">
            {descText}
          </p>

          <div className="hero-cta">
            <button
              className="btn btn-primary"
              type="button"
              id="heroPrimary"
              onClick={() => onOpenDetails(it)}
            >
              <Download className="w-4 h-4" />
              <span>{isMusic ? 'مشاهده قطعات' : 'مشاهده کیفیت‌ها'}</span>
            </button>
            <button
              className="btn btn-ghost"
              type="button"
              id="heroSecondary"
              aria-pressed={isSaved}
              aria-label={
                isSaved
                  ? `حذف ${it.title} از علاقه‌مندی‌ها`
                  : `افزودن ${it.title} به علاقه‌مندی‌ها`
              }
              onClick={() => onToggleFavorite(it)}
            >
              <Heart
                className={`w-4 h-4 ${isSaved ? 'fill-current text-rose-400' : ''}`}
              />
              <span>{isSaved ? 'حذف از علاقه‌مندی‌ها' : 'افزودن به علاقه‌مندی‌ها'}</span>
            </button>
          </div>
        </div>
      </div>

      <div
        className="dots"
        id="heroDots"
        role="tablist"
        aria-label="ناوبری اثرهای شاخص"
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
      >
        {list.map((item, n) => {
          const on = n === activeIndex
          return (
            <span
              key={item.id}
              style={{ position: 'relative', display: 'inline-flex' }}
            >
              <i
                className={`hit ${on ? 'hit-long' : ''}`}
                role="tab"
                aria-label={item.title}
                aria-current={on}
                onClick={() => goTo(n)}
              />
              <button
                type="button"
                aria-hidden="true"
                tabIndex={-1}
                aria-current={on}
                onClick={() => goTo(n)}
              />
            </span>
          )
        })}
      </div>
    </section>
  )
}
