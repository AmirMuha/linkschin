import type { Metadata } from 'next'
import { MediaCategoryPage } from '@/components/MediaCategoryPage'

export const metadata: Metadata = {
  title: 'بازی‌ها | لینک‌چین',
  description: 'جستجو و دریافت لینک مستقیم بازی‌ها از منابع ایرانی',
}

export default function GamesPage() {
  return <MediaCategoryPage category="games" />
}
