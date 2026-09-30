import { test } from 'node:test'
import assert from 'node:assert'
import {
  itemMatchesTier,
  variantsForTier,
  itemMatchesCensorship,
  variantsForCensorship,
} from './filters.ts'
import type { CensorshipStatus, MediaItem, MovieDownloadVariant, SourceAccessTier } from '../types/media.ts'

function variant(over: Partial<MovieDownloadVariant> = {}): MovieDownloadVariant {
  return {
    id: 'v1', quality: '1080p', codec: 'x265', audio_track: 'dub',
    download_url: 'https://cdn/a.mp4', file_size_mb: 1, source_name: 'S',
    is_censored: null, is_premium: false, ...over,
  }
}

function item(tier: SourceAccessTier, status: CensorshipStatus, variants: MovieDownloadVariant[] = []): MediaItem {
  return {
    id: 'i1', title: 'T', category: 'movies', source_id: 's', page_url: 'https://x.com',
    original_title: null, release_year: 2026, poster_url: null, description: null, stream_url: null,
    imdb_rating: null, censorship_status: status, source_access_tier: tier,
    movie_variants: variants, game_releases: [], music_tracks: [],
  }
}

test('itemMatchesTier: free keeps free+freemium, drops premium', () => {
  assert.strictEqual(itemMatchesTier(item('free', 'unspecified'), 'free'), true)
  assert.strictEqual(itemMatchesTier(item('freemium', 'unspecified'), 'free'), true)
  assert.strictEqual(itemMatchesTier(item('premium', 'unspecified'), 'free'), false)
})

test('itemMatchesTier: premium keeps premium+freemium, drops free', () => {
  assert.strictEqual(itemMatchesTier(item('premium', 'unspecified'), 'premium'), true)
  assert.strictEqual(itemMatchesTier(item('freemium', 'unspecified'), 'premium'), true)
  assert.strictEqual(itemMatchesTier(item('free', 'unspecified'), 'premium'), false)
})

test('itemMatchesTier: all is a pass-through', () => {
  for (const tier of ['free', 'premium', 'freemium'] as SourceAccessTier[]) {
    assert.strictEqual(itemMatchesTier(item(tier, 'unspecified'), 'all'), true)
  }
})

test('variantsForTier: free hides premium rows, premium hides free rows', () => {
  const rows = [variant({ id: 'a' }), variant({ id: 'b', is_premium: true })]
  assert.deepStrictEqual(variantsForTier(rows, 'free').map((v) => v.id), ['a'])
  assert.deepStrictEqual(variantsForTier(rows, 'premium').map((v) => v.id), ['b'])
})

test('variantsForTier: all returns the input untouched', () => {
  const rows = [variant()]
  assert.strictEqual(variantsForTier(rows, 'all'), rows)
})

test('itemMatchesCensorship: uncensored keeps uncensored+mixed, drops censored+unspecified', () => {
  assert.strictEqual(itemMatchesCensorship(item('free', 'uncensored'), 'uncensored'), true)
  assert.strictEqual(itemMatchesCensorship(item('free', 'mixed'), 'uncensored'), true)
  assert.strictEqual(itemMatchesCensorship(item('free', 'censored'), 'uncensored'), false)
  assert.strictEqual(itemMatchesCensorship(item('free', 'unspecified'), 'uncensored'), false)
})

test('itemMatchesCensorship: censored keeps censored+mixed, drops uncensored+unspecified', () => {
  assert.strictEqual(itemMatchesCensorship(item('free', 'censored'), 'censored'), true)
  assert.strictEqual(itemMatchesCensorship(item('free', 'mixed'), 'censored'), true)
  assert.strictEqual(itemMatchesCensorship(item('free', 'uncensored'), 'censored'), false)
  assert.strictEqual(itemMatchesCensorship(item('free', 'unspecified'), 'censored'), false)
})

test('variantsForCensorship: null is_censored hides under either strict filter', () => {
  const rows = [
    variant({ id: 'c', is_censored: true }),
    variant({ id: 'u', is_censored: false }),
    variant({ id: 'n', is_censored: null }),
  ]
  assert.deepStrictEqual(variantsForCensorship(rows, 'uncensored').map((v) => v.id), ['u'])
  assert.deepStrictEqual(variantsForCensorship(rows, 'censored').map((v) => v.id), ['c'])
  assert.deepStrictEqual(variantsForCensorship(rows, 'all').map((v) => v.id), ['c', 'u', 'n'])
})
