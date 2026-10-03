import { test } from 'node:test'
import assert from 'node:assert'
import {
  DEFAULT_META,
  FAVORITES_KEY,
  LEGACY_WATCHLIST_KEY,
  loadFavorites,
  writeFavorites,
} from './favorites.ts'

function memStore(seed: Record<string, string> = {}): Storage {
  const map = new Map(Object.entries(seed))
  return {
    get length() {
      return map.size
    },
    clear: () => map.clear(),
    key: (i: number) => Array.from(map.keys())[i] ?? null,
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
  } as Storage
}

test('loads a stored favorites envelope', () => {
  const s = memStore({ [FAVORITES_KEY]: JSON.stringify({ items: ['a', 'b'], metadata: {} }) })
  const out = loadFavorites(s)
  assert.deepEqual(out.ids, ['a', 'b'])
  assert.equal(out.corrupted, false)
})

test('drops non-string ids rather than trusting storage', () => {
  const s = memStore({ [FAVORITES_KEY]: JSON.stringify({ items: ['a', 7, null, 'b'] }) })
  assert.deepEqual(loadFavorites(s).ids, ['a', 'b'])
})

test('migrates a legacy watchlist once and deletes the old key', () => {
  const s = memStore({ [LEGACY_WATCHLIST_KEY]: JSON.stringify(['digger', 'sogand']) })
  const out = loadFavorites(s)
  assert.deepEqual(out.ids, ['digger', 'sogand'])
  assert.equal(s.getItem(LEGACY_WATCHLIST_KEY), null)
  const written = JSON.parse(s.getItem(FAVORITES_KEY)!)
  assert.deepEqual(written.items, ['digger', 'sogand'])
  assert.equal(written.metadata.migratedFromWatchlist, true)
  assert.equal(typeof written.metadata.migrationTimestamp, 'number')
})

test('a corrupt watchlist migrates empty and is retired', () => {
  const s = memStore({ [LEGACY_WATCHLIST_KEY]: 'not-json{[' })
  const out = loadFavorites(s)
  assert.deepEqual(out.ids, [])
  assert.equal(out.corrupted, true)
  assert.equal(s.getItem(LEGACY_WATCHLIST_KEY), null)
})

test('a corrupt favorites key degrades to an empty collection', () => {
  const s = memStore({ [FAVORITES_KEY]: '"not-valid-json{["' })
  const out = loadFavorites(s)
  assert.deepEqual(out.ids, [])
  assert.equal(out.corrupted, true)
})

test('existing favorites win over a legacy watchlist', () => {
  const s = memStore({
    [FAVORITES_KEY]: JSON.stringify({ items: ['kept'], metadata: DEFAULT_META }),
    [LEGACY_WATCHLIST_KEY]: JSON.stringify(['stale']),
  })
  const out = loadFavorites(s)
  assert.deepEqual(out.ids, ['kept'])
  assert.equal(out.meta.migratedFromWatchlist, false)
  // The legacy key is left alone: this collection is already migrated.
  assert.notEqual(s.getItem(LEGACY_WATCHLIST_KEY), null)
})

test('an empty collection removes the key entirely', () => {
  const s = memStore({ [FAVORITES_KEY]: JSON.stringify({ items: ['a'], metadata: DEFAULT_META }) })
  writeFavorites(s, [], DEFAULT_META)
  assert.equal(s.getItem(FAVORITES_KEY), null)
})

test('a storage that refuses writes still loads', () => {
  const s = memStore({ [FAVORITES_KEY]: JSON.stringify({ items: ['a'], metadata: DEFAULT_META }) })
  const blocked = Object.create(s, {
    setItem: { value: () => { throw new Error('QuotaExceededError') } },
  }) as Storage
  assert.throws(() => writeFavorites(blocked, ['a', 'b'], DEFAULT_META))
})
