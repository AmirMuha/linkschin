import type { Metadata } from 'next'
import { MediaCategoryPage } from '@/components/MediaCategoryPage'

export const metadata: Metadata = {
  title: 'فیلم و سریال | لینک‌چین',
  description: 'جستجو و دریافت لینک مستقیم فیلم و سریال از منابع ایرانی',
}

export default function MoviesPage() {
  return <MediaCategoryPage category="movies" />
}
