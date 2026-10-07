// Shared display helpers. Formatting only — records come from the API.

const AR_DIGITS = '٠١٢٣٤٥٦٧٨٩'
const FA_DIGITS = '۰۱۲۳۴۵۶۷۸۹'

export function normalizeFa(input: string | null | undefined): string {
  const s = String(input ?? '')
  let out = ''
  for (let i = 0; i < s.length; i++) {
    const ch = s[i]
    const ai = AR_DIGITS.indexOf(ch)
    if (ai > -1) {
      out += FA_DIGITS[ai]
      continue
    }
    if (ch === 'ي' || ch === 'ى') {
      out += 'ی'
      continue
    }
    if (ch === 'ك') {
      out += 'ک'
      continue
    }
    if (ch === 'ة') {
      out += 'ه'
      continue
    }
    if (ch === 'ـ') continue
    out += ch
  }
  return out
    .replace(/‌/g, ' ')
    .replace(/[ً-ٟ]/g, '')
    .replace(/[ً-ْ]/g, '')
    .replace(/[۰-۹]/g, (d) => String(FA_DIGITS.indexOf(d)))
    .replace(/[٠-٩]/g, (d) => String(AR_DIGITS.indexOf(d)))
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
}

export function toFaDigits(n: number | string): string {
  return String(n).replace(/\d/g, (d) => FA_DIGITS[+d])
}

export function fmtMiB(bytes: number): string {
  const v = bytes / 1048576
  return v >= 1024 ? `${(v / 1024).toFixed(2)} GB` : `${v.toFixed(0)} MB`
}
