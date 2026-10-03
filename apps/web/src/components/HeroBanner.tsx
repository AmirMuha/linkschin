'use client'

import React, { useState, useEffect } from 'react'
import type { Category } from '@/types/media'
import type { CatalogItem, CatalogMovie, CatalogGame, CatalogMusic } from '@/lib/catalog'
import { toFaDigits, getCatalogItemById } from '@/lib/catalog'
import { Download, Heart } from 'lucide-react'

interface HeroBannerProps {
  category: Category
  onOpenDetails: (item: CatalogItem) => void
  onToggleFavorite: (item: CatalogItem) => void
  isItemFavorite: (id: string) => boolean
}

const HERO_POOLS: Record<Category, string[]> = {
  movies: ['digger', 'the-uprising', 'verity', 'war', 'east-of-eden', 'scrubs'],
  games: ['baldurs-gate-3', 'cyberpunk-2077', 'red-dead-redemption-2', 'elden-ring'],
  music: ['sogand', 'googoosh', 'parchame-sefid', 'zendouni'],
}

const HERO_INTERVAL_MS = 6000
const REDUCED_MOTION = '(prefers-reduced-motion: reduce)'

// Games ship square key art under /keys/, everything else a landscape backdrop.
function backdropFor(category: Category, it: CatalogItem): string {
  return category === 'games' ? `/images/keys/${it.id}.jpg` : `/images/backdrops/${it.id}.jpg`
}

export function HeroBanner({
  category,
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
  }, [category])

  useEffect(() => {
    const onVisibility = () => setHidden(document.hidden)
    document.addEventListener('visibilitychange', onVisibility)
    return () => document.removeEventListener('visibilitychange', onVisibility)
  }, [])

  const ids = HERO_POOLS[category] || []
  const list = ids
    .map((id) => getCatalogItemById(id))
    .filter((it): it is CatalogItem => Boolean(it))
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

  // Warm the next slide's art. Backdrops are 3840x2160 and up to 2.4 MB, so
  // without this the hero paints empty for a beat on every advance.
  const nextItem = list[(activeIndex + 1) % count]
  const nextSrc = nextItem
    ? isMusic
      ? nextItem.art
      : backdropFor(category, nextItem)
    : null

  useEffect(() => {
    if (nextSrc) new Image().src = nextSrc
  }, [nextSrc])

  if (count === 0) return null

  const it = list[activeIndex]
  const isSaved = isItemFavorite(it.id)

  const backdropSrc = backdropFor(category, it)
  const goTo = (n: number) => {
    setIndex(n)
    setNav((v) => v + 1)
  }

  const eyebrowText =
    category === 'games'
      ? (it as CatalogGame).releaseGroup
      : category === 'music'
        ? 'آلبوم'
        : (it as CatalogMovie).kind === 'tv'
          ? 'سریال'
          : 'فیلم سینمایی'

  const metaText =
    category === 'music'
      ? `${it.title} · ${toFaDigits(it.year)}`
      : `${
          (it as CatalogMovie | CatalogGame).kind === 'game'
            ? 'ریپک'
            : (it as CatalogMovie).kind === 'tv'
              ? 'تلویزیونی'
              : 'فیلم'
        } · ${toFaDigits(it.year)}`

  const descText =
    category === 'music' ? (
      <>
        {toFaDigits((it as CatalogMusic).tracks.length)} قطعه با زمان‌بندی واقعی. ابتدا پیش‌نمایش را
        در همین صفحه ببینید، سپس فایل MP3 را با کیفیت <bdi dir="ltr">128</bdi> یا{' '}
        <bdi dir="ltr">320 kbps</bdi> مستقیم از CDN منبع بگیرید.
      </>
    ) : (
      it.blurb
    )

  const titleText =
    category === 'music'
      ? (it as CatalogMusic).artist.toUpperCase()
      : it.title.toUpperCase()

  return (
    <section className="wrap" data-od-id="hero-section" aria-label="اثر شاخص">
      <div className={`hero ${isMusic ? 'cover' : ''}`} id="hero">
        {!isMusic && (
          <img
            key={it.id}
            className="hero-shot"
            src={backdropSrc}
            alt={`تصویر شاخص ${it.title}`}
            width={3840}
            height={2160}
            onError={(e) => {
              ;(e.target as HTMLImageElement).src = it.art
            }}
          />
        )}

        {isMusic && (
          <div className="cover-cell">
            <img key={it.id} src={it.art} alt={`کاور ${it.title}`} />
          </div>
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
                className={item.cat === 'music' ? 'sq' : ''}
                aria-current={isCurrent}
                aria-label={`نمایش ${item.title}`}
                onClick={() => goTo(n)}
              >
                <img src={item.art} alt="" loading="lazy" />
              </button>
            )
          })}
        </div>

        <div className="hero-body">
          <div className="eyebrow">
            <span className="pill-red" id="heroEyebrow">
              {eyebrowText}
            </span>
            <span className="pill-ghost" id="heroMeta">
              {metaText}
            </span>
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
