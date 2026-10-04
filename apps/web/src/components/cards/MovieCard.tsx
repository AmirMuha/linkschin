'use client'

import React, { useState } from 'react'
import type { MediaItem } from '@/types/media'
import { Film, PlayCircle, Calendar, ExternalLink, Star, Eye } from 'lucide-react'
import { MovieDownloadMatrix } from './MovieDownloadMatrix'
import { TechnicalText } from '@/components/ui/TechnicalText'
import type { CensorshipStatus, SourceAccessTier } from '@/types/media'
import type { CensorshipFilter, TierFilter } from '@/lib/urlFilters'

export const CENSORSHIP_BADGE: Record<CensorshipStatus, { label: string; className: string }> = {
  uncensored: {
    label: 'نسخه کامل',
    className: 'bg-emerald-950/80 text-emerald-300 border-emerald-800/60',
  },
  censored: {
    label: 'بازبینی شده',
    className: 'bg-amber-950/80 text-amber-300 border-amber-800/60',
  },
  mixed: {
    label: 'شامل هر دو نسخه',
    className: 'bg-cyan-950/80 text-cyan-300 border-cyan-800/60',
  },
  unspecified: {
    label: 'نامشخص',
    className: 'bg-zinc-900/80 text-zinc-400 border-zinc-700/60',
  },
}

export const TIER_BADGE: Record<SourceAccessTier, { label: string; title: string; className: string }> = {
  free: { label: 'رایگان', title: 'دسترسی کاملاً رایگان', className: 'bg-zinc-950/80 text-zinc-300 border-zinc-800/80' },
  premium: { label: 'VIP', title: 'فقط با خرید اشتراک سایت منبع', className: 'bg-amber-500/20 text-amber-300 border-amber-500/40' },
  freemium: { label: 'رایگان و VIP', title: 'شامل لینک‌های رایگان و پولی', className: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40' },
}

interface MovieCardProps {
  item: MediaItem
  onPlayStream?: (streamUrl: string, title: string) => void
  activeTierFilter?: TierFilter
  activeCensorshipFilter?: CensorshipFilter
}

export function MovieCard({
  item,
  onPlayStream,
  activeTierFilter = 'all',
  activeCensorshipFilter = 'all',
}: MovieCardProps) {
  const [imageError, setImageError] = useState(false)

  // FR-017: the server drops an item that has neither a download nor a watch page, so
  // `movie_variants` is empty here only for a genuine watch-only source. Guarded
  // anyway: an unfiltered list can still yield empty variants, and a dead link to
  // undefined is worse than no button.
  const hasDownload = (item.movie_variants?.length ?? 0) > 0
  const watchUrl = item.watch_url ?? ''

  return (
    <article
      className="card"
      style={{ cursor: 'default' }}
    >
      {/* Poster Image / Header */}
      <div className="card-art mb-4">
        {item.poster_url && !imageError ? (
          <img
            src={item.poster_url}
            alt={item.title}
            onError={() => setImageError(true)}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center text-zinc-600 gap-2">
            <Film className="w-12 h-12" />
            <span className="text-xs">بدون تصویر</span>
          </div>
        )}

        {/* Floating Stream Preview Trigger */}
        {item.stream_url && onPlayStream && (
          <button
            type="button"
            onClick={() => onPlayStream(item.stream_url!, item.title)}
            className="absolute inset-0 m-auto w-12 h-12 rounded-full bg-cyan-500/90 text-slate-950 flex items-center justify-center shadow-2xl opacity-90 group-hover:opacity-100 hover:scale-110 transition-all backdrop-blur-sm"
            aria-label={`پخش پیش‌نمایش ${item.title}`}
          >
            <PlayCircle className="w-7 h-7 fill-slate-950 text-cyan-500" />
          </button>
        )}

        {/* Source Badge */}
        <div className="absolute top-2.5 start-2.5 flex items-center gap-1 px-2.5 py-1 rounded-full bg-zinc-950/80 border border-zinc-800/80 text-2xs text-zinc-300 font-medium backdrop-blur-md">
          <span>{item.source_id}</span>
        </div>

        {/* Year Badge */}
        {item.release_year && (
          <div className="absolute top-2.5 end-2.5 flex items-center gap-1 px-2 py-0.5 rounded-full bg-zinc-950/80 border border-zinc-800/80 text-2xs font-mono text-zinc-300 backdrop-blur-md">
            <Calendar className="w-3 h-3 text-cyan-400" />
            <TechnicalText>{item.release_year}</TechnicalText>
          </div>
        )}

        {/* IMDb Rating — always rendered, with a fixed-width score so the badge is
            identical whether the score is 7.9 or the unrated em-dash (SC-002). */}
        <div className="absolute bottom-2.5 start-2.5 flex items-center gap-1 px-2 py-0.5 rounded-full bg-zinc-950/80 border border-zinc-800/80 font-mono text-2xs text-amber-300 backdrop-blur-md">
          <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
          <span className="inline-block w-[2.5ch] text-center">
            {item.imdb_rating?.toFixed(1) ?? '—'}
          </span>
        </div>

        {/* Source access tier */}
        <div
          className={`absolute bottom-2.5 end-2.5 px-2 py-0.5 rounded-full border text-2xs font-medium backdrop-blur-md ${TIER_BADGE[item.source_access_tier].className}`}
          title={TIER_BADGE[item.source_access_tier].title}
        >
          {TIER_BADGE[item.source_access_tier].label}
        </div>

        {/* Censorship status */}
        <div
          className={`absolute bottom-11 start-2.5 px-2 py-0.5 rounded-full border text-2xs font-medium backdrop-blur-md ${CENSORSHIP_BADGE[item.censorship_status].className}`}
        >
          {CENSORSHIP_BADGE[item.censorship_status].label}
        </div>
      </div>

      {/* Title & Metadata */}
      <div className="card-body mb-2">
        <h3 className="card-title" title={item.title}>
          {item.title}
        </h3>

        {item.original_title && (
          <TechnicalText className="text-xs text-zinc-400 line-clamp-1">
            {item.original_title}
          </TechnicalText>
        )}
      </div>

      {/* Description Snippet */}
      {item.description && (
        <p
          className="text-xs text-zinc-400 line-clamp-2 leading-relaxed mb-3"
          title={item.description}
        >
          {item.description}
        </p>
      )}

      {/* Source page external link */}
      <a
        href={item.page_url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 text-2xs text-zinc-500 hover:text-cyan-400 transition-colors self-start mb-2"
      >
        <span>مشاهده در سایت مرجع</span>
        <ExternalLink className="w-3 h-3" />
      </a>

      {/* Download Variants Matrix — or, for a watch-only source, a watch action
          (FR-006, FR-017). The two are mutually exclusive: a card that offers a
          download must not also offer "watch", or the user cannot tell whether the
          source actually has a public file. */}
      <div className="mt-auto border-t border-zinc-800/80 pt-2">
        {hasDownload ? (
          <MovieDownloadMatrix
            variants={item.movie_variants}
            activeTierFilter={activeTierFilter}
            activeCensorshipFilter={activeCensorshipFilter}
          />
        ) : (
          <a
            href={watchUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 w-full px-3 py-2 rounded-xl bg-violet-500/15 border border-violet-500/40 text-violet-300 hover:bg-violet-500/25 hover:border-violet-400/60 transition-colors text-xs sm:text-sm font-medium"
            aria-label={`مشاهده ${item.title} در سایت منبع`}
          >
            <Eye className="w-4 h-4 shrink-0" />
            <span>مشاهده در سایت منبع</span>
            <ExternalLink className="w-3 h-3 shrink-0" />
          </a>
        )}
      </div>
    </article>
  )
}
