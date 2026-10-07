'use client'

import React, { useState } from 'react'
import type { MediaItem } from '@/types/media'
import { Gamepad2, HardDrive, Tag, ExternalLink, Calendar, Star } from 'lucide-react'
import { TechnicalText } from '@/components/ui/TechnicalText'
import { TIER_BADGE } from './MovieCard'
import { FavoriteButton } from './FavoriteButton'

export interface GameCardProps {
  item: MediaItem
  onOpenDetails?: (item: MediaItem) => void
  onToggleFavorite?: (item: MediaItem) => void
  isItemFavorite?: (id: string) => boolean
}

export function GameCard({
  item,
  onOpenDetails,
  onToggleFavorite,
  isItemFavorite,
}: GameCardProps) {
  const [imageError, setImageError] = useState(false)
  const primaryRelease = item.game_releases?.[0]

  return (
    <article
      className="card group"
      style={{ cursor: 'pointer' }}
      onClick={() => onOpenDetails?.(item)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onOpenDetails?.(item)
        }
      }}
      aria-label={`مشاهده جزئیات و دانلود ${item.title}`}
    >
      {/* Cover Artwork */}
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
            <Gamepad2 className="w-12 h-12" />
            <span className="text-xs">بدون تصویر</span>
          </div>
        )}

        {/* Source Badge */}
        <div className="absolute top-2.5 start-2.5 flex items-center gap-1 px-2.5 py-1 rounded-full bg-zinc-950/80 border border-zinc-800/80 text-2xs text-zinc-300 font-medium backdrop-blur-md">
          <span>{item.source_id}</span>
        </div>

        <FavoriteButton
          item={item}
          onToggleFavorite={onToggleFavorite}
          isItemFavorite={isItemFavorite}
          className="below"
        />

        {/* Year Badge */}
        {item.release_year ? (
          <div className="absolute top-2.5 end-2.5 flex items-center gap-1 px-2 py-0.5 rounded-full bg-zinc-950/80 border border-zinc-800/80 text-2xs font-mono text-zinc-300 backdrop-blur-md">
            <Calendar className="w-3 h-3 text-cyan-400" />
            <TechnicalText>{item.release_year}</TechnicalText>
          </div>
        ) : primaryRelease?.total_size ? (
          <div className="absolute top-2.5 end-2.5 flex items-center gap-1 px-2 py-0.5 rounded-full bg-zinc-950/80 border border-zinc-800/80 text-2xs font-mono text-zinc-300 backdrop-blur-md">
            <HardDrive className="w-3 h-3 text-cyan-400" />
            <TechnicalText>{primaryRelease.total_size}</TechnicalText>
          </div>
        ) : null}

        {/* Rating or Total Size Badge */}
        {item.imdb_rating != null ? (
          <div className="absolute bottom-2.5 start-2.5 flex items-center gap-1 px-2 py-0.5 rounded-full bg-zinc-950/80 border border-zinc-800/80 font-mono text-2xs text-amber-300 backdrop-blur-md">
            <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
            <span className="inline-block w-[2.5ch] text-center">
              {item.imdb_rating.toFixed(1)}
            </span>
          </div>
        ) : primaryRelease?.total_size && item.release_year ? (
          <div className="absolute bottom-2.5 start-2.5 flex items-center gap-1 px-2 py-0.5 rounded-full bg-zinc-950/80 border border-zinc-800/80 font-mono text-2xs text-zinc-300 backdrop-blur-md">
            <HardDrive className="w-3 h-3 text-cyan-400" />
            <TechnicalText>{primaryRelease.total_size}</TechnicalText>
          </div>
        ) : null}

        {/* Source Access Tier */}
        {item.source_access_tier && TIER_BADGE[item.source_access_tier] && (
          <div
            className={`absolute bottom-2.5 end-2.5 px-2 py-0.5 rounded-full border text-2xs font-medium backdrop-blur-md ${TIER_BADGE[item.source_access_tier].className}`}
            title={TIER_BADGE[item.source_access_tier].title}
          >
            {TIER_BADGE[item.source_access_tier].label}
          </div>
        )}
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

      {/* Release Group & Version */}
      {primaryRelease && (
        <div className="flex items-center gap-2 flex-wrap text-2xs mb-2">
          {primaryRelease.release_group && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-zinc-800 border border-zinc-700/60 text-zinc-300">
              <Tag className="w-3 h-3 text-cyan-400" />
              <TechnicalText>{primaryRelease.release_group}</TechnicalText>
            </span>
          )}

          {primaryRelease.version && (
            <span className="px-2 py-0.5 rounded-md bg-zinc-800/70 border border-zinc-700/40 text-zinc-400">
              <TechnicalText>{primaryRelease.version}</TechnicalText>
            </span>
          )}
        </div>
      )}

      {/* Description */}
      {item.description && (
        <p
          className="text-xs text-zinc-400 line-clamp-2 leading-relaxed mb-3"
          title={item.description}
        >
          {item.description}
        </p>
      )}

      {/* Source page link */}
      <a
        href={item.page_url}
        target="_blank"
        rel="noopener noreferrer"
        onClick={(e) => e.stopPropagation()}
        className="inline-flex items-center gap-1 text-2xs text-zinc-500 hover:text-cyan-400 transition-colors self-start mt-auto pt-1"
      >
        <span>مشاهده در سایت مرجع</span>
        <ExternalLink className="w-3 h-3" />
      </a>
    </article>
  )
}
