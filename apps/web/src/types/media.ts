export type Category = 'movies' | 'games' | 'music'

export type LinkAccess = 'direct' | 'needs_login'
export type SourceAccessTier = 'free' | 'premium' | 'freemium'
export type CensorshipStatus = 'uncensored' | 'censored' | 'mixed' | 'unspecified'

/** Operational state of a source (FR-008), mirrored from the server's SourceState enum. */
export type SourceState =
  | 'providing_results'
  | 'subscription_only'
  | 'unreachable'
  | 'requires_login'
  | 'not_yet_proven'

export interface MovieDownloadVariant {
  id: string
  quality: string
  codec: string
  audio_track: string
  download_url: string
  file_size_mb: number | null
  source_name: string
  access?: LinkAccess
  is_censored?: boolean | null
  is_premium?: boolean
}

export interface GamePartLink {
  part_number: number
  part_label: string
  download_url: string
  file_size: string | null
  access?: LinkAccess
}

export interface GameRelease {
  id: string
  source_name: string
  release_group: string
  version: string
  total_size: string
  archive_password: string
  parts: GamePartLink[]
  has_missing_parts: boolean
  missing_part_numbers: number[]
}

export interface MusicDownloadVariant {
  bitrate: string
  download_url: string
  file_size: string | null
  access?: LinkAccess
}

export interface MusicTrack {
  id: string
  title: string
  artist: string
  source_name: string
  album: string | null
  cover_url: string | null
  stream_url: string | null
  downloads: MusicDownloadVariant[]
}

export interface MediaItem {
  id: string
  title: string
  category: Category
  source_id: string
  page_url: string
  original_title: string | null
  release_year: number | null
  poster_url: string | null
  description: string | null
  stream_url: string | null
  /**
   * A page on the source's own site where the title is watchable, for sources with
   * no public download (FR-006). Deliberately distinct from `stream_url`, which is a
   * playable file: nothing here is fetched, buffered or relayed (FR-026). Optional so
   * a pre-005 server response still typechecks; absence means "no watch page".
   */
  watch_url?: string | null
  imdb_rating: number | null
  censorship_status: CensorshipStatus
  source_access_tier: SourceAccessTier
  movie_variants: MovieDownloadVariant[]
  game_releases: GameRelease[]
  music_tracks: MusicTrack[]
  /** Absent on a pre-006 server; absence means "full" (search contract, client obligation 3). */
  source_kind?: 'full' | 'reference'
}

export interface SearchApiResponse {
  query: string
  category: string
  is_cached: boolean
  warnings: string[]
  items: MediaItem[]
}

export interface SourceStatus {
  id: string
  name: string
  category: string
  base_url: string
  enabled: boolean
  /** Optional so a pre-006 server response still typechecks (sources contract, G4). */
  kind?: 'full' | 'reference'
  /** Derived: inactive when not enabled, degraded at 3+ consecutive failures. */
  status?: 'active' | 'degraded' | 'inactive'
  /** Non-null and specific whenever status is not "active". */
  inactive_reason?: string | null
  consecutive_failures?: number
  access_tier: SourceAccessTier
  /** 005: false when the source hands back a watch page rather than a download. */
  provides_downloads?: boolean
  /** 005: the server's own view of the source, as opposed to the derived status. */
  state?: SourceState
  last_reachable_at?: string | null
  /** The address that actually answered, when it is not the first one configured. */
  active_address?: string | null
}
