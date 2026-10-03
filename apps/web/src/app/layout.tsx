import type { Metadata } from 'next'
import { Vazirmatn } from 'next/font/google'
import { ToastProvider } from '@/components/ui/ToastNotification'
import './globals.css'

const vazirmatn = Vazirmatn({
  subsets: ['arabic', 'latin'],
  variable: '--font-vazirmatn',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Linkschin | موتور جستجوی چندرسانه‌ای',
  description: 'دریافت مستقیم لینک‌های دانلود فیلم، سریال، بازی و موسیقی بدون واسطه و تبلیغات',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="fa" dir="rtl" className={vazirmatn.variable}>
      <body className="font-sans antialiased selection:bg-cyan-500/30 selection:text-cyan-200">
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  )
}
