'use client'

import React from 'react'
import Link from 'next/link'
import type { Category } from '@/types/media'
import type { CatalogItem } from '@/lib/catalog'
import {
  CATALOG_MOVIES,
  CATALOG_GAMES,
  CATALOG_MUSIC,
  CATALOG_SOURCES,
  toFaDigits,
} from '@/lib/catalog'
import { CatalogCard } from '@/components/CatalogCard'
import { ChevronDown } from 'lucide-react'

interface StaticSectionsProps {
  category: Category
  onOpenDetails: (item: CatalogItem) => void
  onToggleFavorite: (item: CatalogItem) => void
  isItemFavorite: (id: string) => boolean
  dynamicTrending?: any[]
  dynamicLatest?: any[]
}

const FAQ_ITEMS = [
  {
    q: 'Does this server host or stream any file?',
    a: 'No. The aggregator resolves metadata and direct upstream URLs and hands them to your browser. Video, audio and archives travel directly between your client and the upstream CDN, so the server consumes no media bandwidth at all.',
  },
  {
    q: 'Why does a result have more than one quality?',
    a: 'Every movie resolves into variants segmented by resolution (480p / 720p / 1080p / 4K), codec (x264, x265 / HEVC, 10-bit) and audio track (Persian dubbed, Persian soft-sub, or original). Each variant is a separate direct link.',
  },
  {
    q: 'Why does a game release show a gap in its parts?',
    a: 'Some portals publish Part 1, 2 and 4 but not 3. The missing segment is highlighted rather than silently renumbered, so a download manager cannot quietly produce a corrupt archive.',
  },
  {
    q: 'Can I search in Persian?',
    a: 'Yes. Queries are normalised before they leave the server: Arabic ي and ك fold onto Persian ی and ک, Arabic-Indic digits ٠-٩ become Persian ۰-۹, and the zero-width non-joiner is treated as a space so mixed-script queries still match.',
  },
  {
    q: 'What happens when a source is down?',
    a: 'Healthy sources still answer and the page renders, with a non-intrusive notice naming the unavailable portals. A music source that fails three consecutive searches is marked degraded and falls back; a source you hide is excluded from every later query.',
  },
  {
    q: 'Are VIP or credential-gated links included?',
    a: 'No. Extraction is restricted to publicly available, unauthenticated links. Paid walls, account requirements and token-protected players are skipped rather than bypassed.',
  },
]

const RESOLVE_STEPS = [
  {
    step: '1 · Normalise',
    desc: 'Arabic ي and ك fold onto Persian ی and ک, Arabic-Indic digits become Persian ones, and ZWNJ becomes a plain space so a mixed-script query still matches.',
  },
  {
    step: '2 · Fan out',
    desc: 'Every enabled source for the active category runs concurrently under one global timeout budget, so one slow portal cannot stall the page.',
  },
  {
    step: '3 · Merge + rank',
    desc: 'Results merge into one ranked list per FR-002. Nothing crosses category boundaries — the category you are in is the only one that queries.',
  },
  {
    step: '4 · Link straight out',
    desc: 'Formats, parts and bitrate tiers are handed to your browser as upstream URLs. Expired token risk is handled by a 30–60 minute result cache.',
  },
]

export function StaticSections({
  category,
  onOpenDetails,
  onToggleFavorite,
  isItemFavorite,
  dynamicTrending = [],
  dynamicLatest = [],
}: StaticSectionsProps) {
  const pool =
    category === 'movies'
      ? CATALOG_MOVIES
      : category === 'games'
        ? CATALOG_GAMES
        : CATALOG_MUSIC

  const trendTitle =
    category === 'movies'
      ? 'Trending today'
      : category === 'games'
        ? 'Popular game releases'
        : 'Trending tracks'

  const trendSub =
    category === 'music'
      ? 'cover art, artist and bitrate tiers'
      : category === 'games'
        ? 'multi-part archives with extraction passwords'
        : 'rating from upstream metadata'

  const latestTitle =
    category === 'movies'
      ? 'Latest this year'
      : category === 'games'
        ? 'Freshly indexed'
        : 'New releases'

  // Trending: dynamic from API or fallback
  const trendingItems = (dynamicTrending && dynamicTrending.length > 0) ? dynamicTrending : pool.slice(0, 12)
  // Latest: dynamic from API or fallback
  const latestItems = (dynamicLatest && dynamicLatest.length > 0) ? dynamicLatest : pool.slice(-14)

  // Category sources
  const catSources = CATALOG_SOURCES.filter((s) => s.cat === category)
  const okSources = catSources.filter((s) => s.enabled && s.state === 'ok')
  const warnSources = catSources.filter((s) => s.enabled && s.state === 'warn')
  const offSources = catSources.filter((s) => !s.enabled || s.state === 'bad')
  const ledStatus = warnSources.length > 0 ? 'warn' : 'ok'

  return (
    <>
      {/* Health Strip */}
      <div className="wrap">
        <div className="health" data-od-id="source-health" style={{ marginTop: '16px' }}>
          <span className={`led ${ledStatus}`}></span>
          <strong>
            {toFaDigits(okSources.length)} of {toFaDigits(catSources.length)} sources answered
          </strong>
          <ul>
            {catSources.map((s) => {
              const led = !s.enabled || s.state === 'bad' ? 'bad' : s.state === 'warn' ? 'warn' : 'ok'
              return (
                <li key={s.id} className="chip">
                  <span className={`led ${led}`}></span>
                  <span>{s.name}</span>
                  <span style={{ color: 'var(--muted-2)' }}>{s.tierLabel}</span>
                </li>
              )
            })}
          </ul>
          {offSources.length > 0 && (
            <span style={{ color: 'var(--muted-2)', fontSize: '12px' }}>
              Unavailable: {offSources.map((s) => s.name).join(', ')}
            </span>
          )}
          <Link className="btn btn-quiet btn-sm" href="/sources">
            Manage sources
          </Link>
        </div>
      </div>

      {/* Trending Section */}
      <section className="wrap sec" data-od-id="section-trending" id="trending">
        <div className="sec-head">
          <h2 id="trendTitle">{trendTitle}</h2>
          <span className="sub" id="trendSub">
            {trendSub}
          </span>
        </div>
        <div className="grid grid-6" id="trendGrid">
          {trendingItems.map((item) => (
            <CatalogCard
              key={item.id}
              item={item}
              onClick={() => onOpenDetails(item)}
              onToggleFavorite={onToggleFavorite}
              isItemFavorite={isItemFavorite}
            />
          ))}
        </div>
      </section>

      {/* Latest Shelf Section */}
      <section className="wrap sec" data-od-id="section-latest" id="latest">
        <div className="sec-head">
          <h2 id="latestTitle">{latestTitle}</h2>
          <span className="sub">sorted by release date</span>
        </div>
        <div className="shelf no-sb" id="latestShelf">
          {latestItems.map((item) => (
            <CatalogCard
              key={item.id}
              item={item}
              onClick={() => onOpenDetails(item)}
              onToggleFavorite={onToggleFavorite}
              isItemFavorite={isItemFavorite}
            />
          ))}
        </div>
      </section>

      {/* Why Section */}
      <section className="wrap sec" data-od-id="section-why" id="why">
        <div className="notice" style={{ marginBottom: '20px' }}>
          <span className="led ok"></span>
          <span>
            <strong style={{ color: '#fff' }}>Zero media relaying.</strong> This server resolves
            links and metadata only. Every download and preview connects from your browser straight
            to the upstream CDN — the site stores, hosts and proxies no video, audio or archive.
            The single declared exception is the YouTube → MP3 tool.
          </span>
        </div>
        <div className="sec-head">
          <h2>How a query resolves</h2>
          <span className="sub">scoped to the category you are in</span>
        </div>
        <div
          className="grid"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))' }}
          id="flowGrid"
        >
          {RESOLVE_STEPS.map((step, idx) => (
            <div
              key={idx}
              className="notice"
              style={{
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '8px',
              }}
            >
              <strong
                style={{
                  color: '#fff',
                  fontSize: '13px',
                  letterSpacing: '.1em',
                  textTransform: 'uppercase',
                }}
              >
                {step.step}
              </strong>
              <span>{step.desc}</span>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ Section */}
      <section className="wrap sec" data-od-id="section-faq" id="faq">
        <div
          className="sec-head"
          style={{
            justifyContent: 'center',
            textAlign: 'center',
            display: 'block',
            border: 0,
          }}
        >
          <h2 style={{ color: 'var(--accent)' }}>Support centre</h2>
          <p
            style={{
              marginTop: '10px',
              color: 'var(--muted)',
              fontSize: 'clamp(15px, 1.4vw, 18px)',
            }}
          >
            Frequently asked questions about direct links, caches and censorship filtering.
          </p>
        </div>
        <div className="faq" id="faqList">
          {FAQ_ITEMS.map((item, idx) => (
            <details key={idx} className="q">
              <summary>
                <span>{item.q}</span>
                <span className="caret">
                  <ChevronDown className="w-4 h-4" />
                </span>
              </summary>
              <p>{item.a}</p>
            </details>
          ))}
        </div>
      </section>
    </>
  )
}
