import { test } from 'node:test'
import assert from 'node:assert'
import { sortParts, formatPartLinksForClipboard } from './archive.ts'
import type { GamePartLink } from '../types/media.ts'

test('sortParts correctly sorts parts by part_number ascending', () => {
  const parts: GamePartLink[] = [
    { part_number: 3, part_label: 'Part 3', download_url: 'https://cdn.example.com/part3.rar', file_size: '2GB' },
    { part_number: 1, part_label: 'Part 1', download_url: 'https://cdn.example.com/part1.rar', file_size: '2GB' },
    { part_number: 2, part_label: 'Part 2', download_url: 'https://cdn.example.com/part2.rar', file_size: '2GB' },
  ]

  const sorted = sortParts(parts)
  assert.strictEqual(sorted[0].part_number, 1)
  assert.strictEqual(sorted[1].part_number, 2)
  assert.strictEqual(sorted[2].part_number, 3)
})

test('formatPartLinksForClipboard formats links as newline-separated text', () => {
  const parts: GamePartLink[] = [
    { part_number: 2, part_label: 'Part 2', download_url: 'https://cdn.example.com/part2.rar', file_size: null },
    { part_number: 1, part_label: 'Part 1', download_url: 'https://cdn.example.com/part1.rar', file_size: null },
  ]

  const result = formatPartLinksForClipboard(parts)
  assert.strictEqual(
    result,
    'https://cdn.example.com/part1.rar\nhttps://cdn.example.com/part2.rar'
  )
})

test('formatPartLinksForClipboard handles empty or null input gracefully', () => {
  assert.strictEqual(formatPartLinksForClipboard([]), '')
})
