export type NavPage = 'movies' | 'games' | 'music' | 'favorites' | 'sources' | 'mp3'

export const NAV_ITEMS: { href: string; page: NavPage; label: string }[] = [
  { href: '/movies', page: 'movies', label: 'فیلم و سریال' },
  { href: '/games', page: 'games', label: 'بازی‌ها' },
  { href: '/music', page: 'music', label: 'موسیقی' },
  { href: '/favorites', page: 'favorites', label: 'علاقه‌مندی‌ها' },
  { href: '/sources', page: 'sources', label: 'منابع' },
  { href: '/youtube-to-mp3', page: 'mp3', label: 'MP3' },
]

export function resolveNavPage(pathname: string | null | undefined): NavPage | undefined {
  if (!pathname) return undefined
  if (pathname.startsWith('/movies')) return 'movies'
  if (pathname.startsWith('/games')) return 'games'
  if (pathname.startsWith('/music')) return 'music'
  if (pathname.startsWith('/favorites')) return 'favorites'
  if (pathname.startsWith('/sources')) return 'sources'
  if (pathname.startsWith('/youtube-to-mp3')) return 'mp3'
  return undefined
}
