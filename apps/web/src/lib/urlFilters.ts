// URL <-> filter-state mapping for the in-view filter bar (spec 007, FR-012).
// Default values are omitted from the query string so shared URLs stay clean.

export type TierFilter = 'all' | 'free' | 'premium'
export type CensorshipFilter = 'all' | 'uncensored' | 'censored'
/**
 * FR-005: 'downloads' is the default Movies scope -- subscription sources return a
 * watch page and no file, so they are excluded unless the user asks for everything.
 */
export type SourceScopeFilter = 'downloads' | 'all'

const TIERS: readonly TierFilter[] = ['all', 'free', 'premium']
const CENSORSHIP: readonly CensorshipFilter[] = ['all', 'uncensored', 'censored']
const SCOPES: readonly SourceScopeFilter[] = ['downloads', 'all']

export function parseScopeParam(raw: string | null): SourceScopeFilter {
  return SCOPES.includes(raw as SourceScopeFilter) ? (raw as SourceScopeFilter) : 'downloads'
}

export function parseTierParam(raw: string | null): TierFilter {
  return TIERS.includes(raw as TierFilter) ? (raw as TierFilter) : 'all'
}

export function parseCensorshipParam(raw: string | null): CensorshipFilter {
  return CENSORSHIP.includes(raw as CensorshipFilter) ? (raw as CensorshipFilter) : 'all'
}

export function buildSearchParams(
  tier: TierFilter,
  censorship: CensorshipFilter,
  base?: URLSearchParams,
  scope: SourceScopeFilter = 'downloads'
): URLSearchParams {
  const params = new URLSearchParams(base)
  if (tier === 'all') params.delete('tier')
  else params.set('tier', tier)

  if (censorship === 'all') params.delete('censorship')
  else params.set('censorship', censorship)

  // Default omitted, so a shared downloads-only URL is no longer than it was pre-005.
  if (scope === 'downloads') params.delete('scope')
  else params.set('scope', scope)

  return params
}
