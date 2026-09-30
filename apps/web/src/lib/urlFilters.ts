// URL <-> filter-state mapping for the in-view filter bar (spec 007, FR-012).
// Default values are omitted from the query string so shared URLs stay clean.

export type TierFilter = 'all' | 'free' | 'premium'
export type CensorshipFilter = 'all' | 'uncensored' | 'censored'

const TIERS: readonly TierFilter[] = ['all', 'free', 'premium']
const CENSORSHIP: readonly CensorshipFilter[] = ['all', 'uncensored', 'censored']

export function parseTierParam(raw: string | null): TierFilter {
  return TIERS.includes(raw as TierFilter) ? (raw as TierFilter) : 'all'
}

export function parseCensorshipParam(raw: string | null): CensorshipFilter {
  return CENSORSHIP.includes(raw as CensorshipFilter) ? (raw as CensorshipFilter) : 'all'
}

export function buildSearchParams(
  tier: TierFilter,
  censorship: CensorshipFilter,
  base?: URLSearchParams
): URLSearchParams {
  const params = new URLSearchParams(base)
  if (tier === 'all') params.delete('tier')
  else params.set('tier', tier)

  if (censorship === 'all') params.delete('censorship')
  else params.set('censorship', censorship)

  return params
}
