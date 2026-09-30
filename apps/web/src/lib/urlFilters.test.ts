import { test } from 'node:test'
import assert from 'node:assert'
import {
  parseTierParam,
  parseCensorshipParam,
  buildSearchParams,
} from './urlFilters.ts'

test('parseTierParam accepts the three permitted values and rejects anything else', () => {
  assert.strictEqual(parseTierParam('free'), 'free')
  assert.strictEqual(parseTierParam('premium'), 'premium')
  assert.strictEqual(parseTierParam('all'), 'all')
  assert.strictEqual(parseTierParam('freemium'), 'all')
  assert.strictEqual(parseTierParam(null), 'all')
})

test('parseCensorshipParam accepts permitted values and rejects mixed (not a filter value)', () => {
  assert.strictEqual(parseCensorshipParam('uncensored'), 'uncensored')
  assert.strictEqual(parseCensorshipParam('censored'), 'censored')
  assert.strictEqual(parseCensorshipParam('mixed'), 'all')
  assert.strictEqual(parseCensorshipParam(''), 'all')
})

test('buildSearchParams omits defaults so shared URLs stay clean', () => {
  assert.strictEqual(buildSearchParams('all', 'all').toString(), '')
})

test('buildSearchParams writes both filters when both are active', () => {
  const q = buildSearchParams('free', 'uncensored').toString()
  assert.ok(q.includes('tier=free'))
  assert.ok(q.includes('censorship=uncensored'))
})

test('buildSearchParams preserves unrelated params like q and category', () => {
  const base = new URLSearchParams('q=batman&category=movies')
  const q = buildSearchParams('free', 'all', base).toString()
  assert.ok(q.includes('q=batman'))
  assert.ok(q.includes('category=movies'))
  assert.ok(q.includes('tier=free'))
  assert.ok(!q.includes('censorship'))
})

test('buildSearchParams round-trips through the parsers', () => {
  const params = buildSearchParams('premium', 'censored')
  assert.strictEqual(parseTierParam(params.get('tier')), 'premium')
  assert.strictEqual(parseCensorshipParam(params.get('censorship')), 'censored')
})
