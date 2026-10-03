import React from 'react'
import type { CatalogItem, CatalogGame, CatalogMusic } from '@/lib/catalog'
import { toFaDigits } from '@/lib/catalog'

interface CatalogCardProps {
  item: CatalogItem
  onClick: () => void
}

export function CatalogCard({ item, onClick }: CatalogCardProps) {
  const isMusic = item.cat === 'music'

  const metaText = isMusic
    ? `${(item as CatalogMusic).artist} · ${toFaDigits(item.year)}`
    : `${toFaDigits(item.year)} · ${
        item.kind === 'tv' ? 'TV' : item.kind === 'game' ? 'Game' : 'Movie'
      }`

  return (
    <button className="card" type="button" onClick={onClick}>
      <div className={`card-art ${isMusic ? 'square' : ''}`}>
        <img
          src={item.art}
          alt={`${item.title} poster`}
          loading="lazy"
          width={500}
          height={isMusic ? 500 : 750}
        />
        <span className="card-fa">
          {item.cat === 'games' && (
            <span className="tag">{(item as CatalogGame).releaseGroup}</span>
          )}
          {'censored' in item && item.censored && (
            <span className="tag">Censored</span>
          )}
          {isMusic && (
            <span className="tag">
              {(item as CatalogMusic).tracks.length} tracks
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
            <span className="rating none">N/A</span>
          )}
        </span>
      </div>
    </button>
  )
}
