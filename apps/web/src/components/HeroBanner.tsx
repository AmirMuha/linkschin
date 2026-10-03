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

export function HeroBanner({
  category,
  onOpenDetails,
  onToggleFavorite,
  isItemFavorite,
}: HeroBannerProps) {
  const [index, setIndex] = useState(0)

  // Reset index when category switches
  useEffect(() => {
    setIndex(0)
  }, [category])

  const ids = HERO_POOLS[category] || []
  const list = ids
    .map((id) => getCatalogItemById(id))
    .filter((it): it is CatalogItem => Boolean(it))

  if (list.length === 0) return null

  const activeIndex = index % list.length
  const it = list[activeIndex]
  const isMusic = category === 'music'
  const isSaved = isItemFavorite(it.id)

  const backdropSrc =
    category === 'games'
      ? `/images/keys/${it.id}.jpg`
      : `/images/backdrops/${it.id}.jpg`

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
            <img src={it.art} alt={`کاور ${it.title}`} />
          </div>
        )}

        <div className="hero-rail" id="heroRail" aria-label="اثرهای شاخص">
          {list.map((item, n) => {
            const isCurrent = n === activeIndex
            return (
              <button
                key={item.id}
                type="button"
                className={item.cat === 'music' ? 'sq' : ''}
                aria-current={isCurrent}
                aria-label={`نمایش ${item.title}`}
                onClick={() => setIndex(n)}
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
                onClick={() => setIndex(n)}
              />
              <button
                type="button"
                aria-hidden="true"
                tabIndex={-1}
                aria-current={on}
                onClick={() => setIndex(n)}
              />
            </span>
          )
        })}
      </div>
    </section>
  )
}
