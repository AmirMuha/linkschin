import type { Metadata } from 'next'
import { MediaCategoryPage } from '@/components/MediaCategoryPage'

export const metadata: Metadata = {
  title: 'موسیقی | لینک‌چین',
  description: 'جستجو و دریافت لینک مستقیم موسیقی و آلبوم‌ها از منابع ایرانی',
}

export default function MusicPage() {
  return <MediaCategoryPage category="music" />
}
