export type Category = 'movies' | 'games' | 'music'

export interface MovieDownloadVariant {
  id: string
  quality: string
  codec: string
  audio_track: string
  download_url: string
  file_size_mb: number | null
  source_name: string
}

export interface GamePartLink {
  part_number: number
  part_label: string
  download_url: string
  file_size: string | null
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
  movie_variants: MovieDownloadVariant[]
  game_releases: GameRelease[]
  music_tracks: MusicTrack[]
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
}
