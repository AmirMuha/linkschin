'use client'

import React from 'react'
import { Heart } from 'lucide-react'
import type { MediaItem } from '@/types/media'

interface FavoriteButtonProps {
  item: MediaItem
  onToggleFavorite?: (item: MediaItem) => void
  isItemFavorite?: (id: string) => boolean
  /** Extra classes for the circle — e.g. `below` when the year badge owns the corner. */
  className?: string
}

/**
 * Lives inside the card's click target (the card is an `<article>` with its own
 * onClick), so a press here must not also open the details drawer. A `role="button"`
 * span rather than a nested `<button>` keeps the markup valid and lets
 * stopPropagation cover the keyboard path too.
 */
export function FavoriteButton({
  item,
  onToggleFavorite,
  isItemFavorite,
  className = '',
}: FavoriteButtonProps) {
  if (!onToggleFavorite) return null
  const isLiked = isItemFavorite?.(item.id) ?? false

  return (
    <span
      className={`card-fav ${className}`.trim()}
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
      <Heart className={`w-4 h-4 ${isLiked ? 'fill-current text-rose-400' : ''}`} />
    </span>
  )
}
