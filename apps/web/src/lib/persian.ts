/**
 * Normalize Persian/Arabic characters and whitespace for search history and client operations.
 * Note: Server-side normalization in Python handles backend queries.
 */
export function normalizePersian(text: string): string {
  if (!text) return ''
  return text
    .normalize('NFKC')
    .replace(/ي/g, 'ی') // Arabic Yeh -> Persian Yeh
    .replace(/ك/g, 'ک') // Arabic Kaf -> Persian Keheh
    .replace(/‌/g, ' ')     // Zero-width non-joiner -> space
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
}
