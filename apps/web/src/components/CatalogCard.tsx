import React from 'react'
import type { CatalogItem, CatalogGame, CatalogMusic } from '@/lib/catalog'
import { toFaDigits } from '@/lib/catalog'
import { Heart } from 'lucide-react'
import { TechnicalText } from '@/components/ui/TechnicalText'

interface CatalogCardProps {
  item: CatalogItem
  onClick: () => void
  onToggleFavorite?: (item: CatalogItem) => void
  isItemFavorite?: (id: string) => boolean
}

export function CatalogCard({
  item,
  onClick,
  onToggleFavorite,
  isItemFavorite,
}: CatalogCardProps) {
  const isMusic = item.cat === 'music'
  const isLiked = isItemFavorite?.(item.id) ?? false

  const metaText = isMusic
    ? `${(item as CatalogMusic).artist} · ${toFaDigits(item.year)}`
    : `${toFaDigits(item.year)} · ${
        item.kind === 'tv' ? 'سریال' : item.kind === 'game' ? 'بازی' : 'فیلم'
      }`

  return (
    <button className="card" type="button" onClick={onClick}>
      <div className={`card-art ${isMusic ? 'square' : ''}`}>
        <img
          src={item.art}
          alt={`پوستر ${item.title}`}
          loading="lazy"
          width={500}
          height={isMusic ? 500 : 750}
        />
        {onToggleFavorite && (
          <span
            className="card-fav"
            // The heart is a sibling <span> rather than a nested <button>: nesting
            // interactive controls inside the card's button is invalid HTML and
            // breaks keyboard activation. stopPropagation keeps a click here from
            // also firing the card (which opens the details drawer).
            role="button"
            tabIndex={0}
            aria-pressed={isLiked}
            aria-label={
              isLiked
                ? `حذف ${item.title} از علاقه‌مندی‌ها`
                : `افزودن ${item.title} به علاقه‌مندی‌ها`
            }
            onClick={(e) => {
              e.stopPropagation()
              onToggleFavorite(item)
            }}
            onKeyDown={(e) => {
              if (e.key !== 'Enter' && e.key !== ' ') return
              e.preventDefault()
              e.stopPropagation()
              onToggleFavorite(item)
            }}
          >
            <Heart
              className={`w-4 h-4 ${isLiked ? 'fill-current text-rose-400' : ''}`}
            />
          </span>
        )}
        <span className="card-fa">
          {item.cat === 'games' && (
            <span className="tag">
              <TechnicalText>{(item as CatalogGame).releaseGroup}</TechnicalText>
            </span>
          )}
          {'censored' in item && item.censored && (
            <span className="tag">بازبینی‌شده</span>
          )}
          {isMusic && (
            <span className="tag">
              {toFaDigits((item as CatalogMusic).tracks.length)} قطعه
            </span>
          )}
        </span>
      </div>
      <div className="card-body">
        <span className="card-title">{item.title}</span>
        <span className="card-meta">
          <span>{metaText}</span>
          {item.rating != null ? (
            <span className="rating">{item.rating.toFixed(1)}</span>
          ) : (
            <span className="rating none">—</span>
          )}
        </span>
      </div>
    </button>
  )
}
