import { test } from 'node:test'
import assert from 'node:assert'
import { resolveNavPage, NAV_ITEMS } from './nav.ts'

test('resolveNavPage maps all header routes correctly', () => {
  assert.strictEqual(resolveNavPage('/movies'), 'movies')
  assert.strictEqual(resolveNavPage('/games'), 'games')
  assert.strictEqual(resolveNavPage('/music'), 'music')
  assert.strictEqual(resolveNavPage('/favorites'), 'favorites')
  assert.strictEqual(resolveNavPage('/sources'), 'sources')
  assert.strictEqual(resolveNavPage('/youtube-to-mp3'), 'mp3')
})

test('resolveNavPage returns undefined for unknown paths', () => {
  assert.strictEqual(resolveNavPage('/'), undefined)
  assert.strictEqual(resolveNavPage('/unknown'), undefined)
  assert.strictEqual(resolveNavPage(null), undefined)
})

test('NAV_ITEMS contains 6 items with valid paths and pages', () => {
  assert.strictEqual(NAV_ITEMS.length, 6)
  for (const item of NAV_ITEMS) {
    assert.strictEqual(resolveNavPage(item.href), item.page)
  }
})
