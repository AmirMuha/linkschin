export const FAVORITES_KEY = 'linkschin:favorites'
export const LEGACY_WATCHLIST_KEY = 'linkschin:watchlist'

export interface FavoritesMeta {
  migratedFromWatchlist: boolean
  migrationTimestamp: number
  version: string
}

export interface StoredFavorites {
  items: string[]
  metadata: FavoritesMeta
}

export const DEFAULT_META: FavoritesMeta = {
  migratedFromWatchlist: false,
  migrationTimestamp: 0,
  version: '2.0',
}

export interface LoadedFavorites {
  ids: string[]
  meta: FavoritesMeta
  /** The stored JSON was unparseable, so the collection was reset (FR-010). */
  corrupted: boolean
}

/**
 * Accepts the `{ items }` envelope and a bare id array; returns `null` for
 * anything else, so a well-formed JSON string or object without `items` is
 * reported as corruption rather than silently read as "nothing saved".
 */
function parseIds(raw: string | null): string[] | null {
  if (raw === null) return null
  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    return null
  }
  if (Array.isArray(parsed)) return parsed.filter((v): v is string => typeof v === 'string')
  if (parsed && typeof parsed === 'object' && Array.isArray((parsed as StoredFavorites).items)) {
    return (parsed as StoredFavorites).items.filter((v): v is string => typeof v === 'string')
  }
  return null
}

/** An empty collection drops the key, so a reload takes the "nothing saved" path. */
export function writeFavorites(storage: Storage, ids: string[], meta: FavoritesMeta): void {
  if (ids.length === 0) storage.removeItem(FAVORITES_KEY)
  else storage.setItem(FAVORITES_KEY, JSON.stringify({ items: ids, metadata: meta }))
}

/**
 * One-way load: honour `linkschin:favorites`, otherwise carry a legacy
 * `linkschin:watchlist` over once and delete the old key (FR-007).
 * Throws only when the storage itself refuses access.
 */
export function loadFavorites(storage: Storage): LoadedFavorites {
  const stored = parseIds(storage.getItem(FAVORITES_KEY))
  if (stored !== null) return { ids: stored, meta: DEFAULT_META, corrupted: false }

  const rawLegacy = storage.getItem(LEGACY_WATCHLIST_KEY)
  const legacy = parseIds(rawLegacy)
  if (legacy === null) {
    // Unreadable watchlist: carry nothing over, but still retire the old key.
    if (rawLegacy !== null) storage.removeItem(LEGACY_WATCHLIST_KEY)
    return { ids: [], meta: DEFAULT_META, corrupted: true }
  }

  const meta: FavoritesMeta = {
    ...DEFAULT_META,
    migratedFromWatchlist: true,
    migrationTimestamp: Date.now(),
  }
  try {
    writeFavorites(storage, legacy, meta)
  } catch {
    // Storage full or read-only: the in-memory collection still works.
  }
  try {
    storage.removeItem(LEGACY_WATCHLIST_KEY)
  } catch {
    // The migration flag above keeps this one-shot, so a failed cleanup is not fatal.
  }
  return { ids: legacy, meta, corrupted: false }
}
