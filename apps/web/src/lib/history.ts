import { normalizePersian } from './persian'

const STORAGE_KEY = 'recent_searches'
const MAX_HISTORY = 8

export function getRecentSearches(): string[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function addRecentSearch(query: string): string[] {
  if (typeof window === 'undefined') return []
  const clean = query.trim()
  if (!clean) return getRecentSearches()

  const norm = normalizePersian(clean)
  const existing = getRecentSearches()

  // Filter out any existing item with same normalized value
  const filtered = existing.filter((item) => normalizePersian(item) !== norm)
  const updated = [clean, ...filtered].slice(0, MAX_HISTORY)

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
  } catch {
    // Storage quota or privacy mode
  }

  return updated
}

export function clearRecentSearches(): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Ignore
  }
}
