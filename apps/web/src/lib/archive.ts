import type { GamePartLink } from '@/types/media'

/**
 * Sorts game archive parts sequentially by part number.
 */
export function sortParts(parts: GamePartLink[]): GamePartLink[] {
  if (!parts) return []
  return [...parts].sort((a, b) => a.part_number - b.part_number)
}

/**
 * Formats multi-part archive download URLs as newline-separated list
 * for batch ingestion into download managers (IDM, JDownloader, aria2).
 */
export function formatPartLinksForClipboard(parts: GamePartLink[]): string {
  if (!parts || parts.length === 0) return ''
  const sorted = sortParts(parts)
  return sorted.map((p) => p.download_url).join('\n')
}
