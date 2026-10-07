'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  DEFAULT_META,
  loadFavorites,
  writeFavorites,
  type FavoritesMeta,
} from '@/lib/favorites'

export interface Favorites {
  ids: string[]
  /** The stored JSON was unparseable, so the collection was reset (FR-010). */
  corrupted: boolean
  /** The last write was rejected (private mode / quota) — session-only from here. */
  persistenceBlocked: boolean
  isLiked: (id: string) => boolean
  /** Takes the item every caller already has in hand, so it drops straight in. */
  toggle: (item: { id: string }) => void
  remove: (id: string) => void
}

export function useFavorites(): Favorites {
  const [ids, setIds] = useState<string[]>([])
  const [corrupted, setCorrupted] = useState(false)
  const [persistenceBlocked, setPersistenceBlocked] = useState(false)
  // Migration metadata is written once and carried by every later write.
  const meta = useRef<FavoritesMeta>(DEFAULT_META)

  useEffect(() => {
    try {
      const loaded = loadFavorites(window.localStorage)
      meta.current = loaded.meta
      setIds(loaded.ids)
      setCorrupted(loaded.corrupted)
    } catch {
      // Private mode denies the first read too: stay in-memory, toggle still works.
      setPersistenceBlocked(true)
    }
  }, [])

  const apply = useCallback((next: string[]) => {
    setIds(next)
    try {
      writeFavorites(window.localStorage, next, meta.current)
      setPersistenceBlocked(false)
    } catch {
      setPersistenceBlocked(true)
    }
  }, [])

  const remove = useCallback(
    (id: string) => {
      if (!ids.includes(id)) return
      apply(ids.filter((x) => x !== id))
    },
    [apply, ids]
  )

  const toggle = useCallback(
    (item: { id: string }) => {
      const id = item.id
      apply(ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id])
    },
    [apply, ids]
  )

  // ponytail: ids live in this one hook instance, so hearts on the same page stay
  // in step only because their components share it. Lift into a provider if
  // favorites must stay synced across routes without a remount.
  return { ids, corrupted, persistenceBlocked, isLiked: (id) => ids.includes(id), toggle, remove }
}
