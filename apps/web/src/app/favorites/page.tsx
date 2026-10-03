'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { Header } from '@/components/Header'
import { Footer } from '@/components/Footer'
import { CatalogCard } from '@/components/CatalogCard'
import { DetailDrawer } from '@/components/DetailDrawer'
import { useToast } from '@/components/ui/ToastNotification'
import { useFavorites } from '@/hooks/useFavorites'
import { getCatalogItemById, toFaDigits, type CatalogItem } from '@/lib/catalog'
import { Film, Gamepad2, Heart, Music, X } from 'lucide-react'

/** Display order and copy per group; ids carry no category of their own. */
const GROUPS = [
  { key: 'movies', label: 'فیلم و سریال', Icon: Film },
  { key: 'games', label: 'بازی‌ها', Icon: Gamepad2 },
  { key: 'music', label: 'موسیقی', Icon: Music },
] as const

export default function FavoritesPage() {
  const favorites = useFavorites()
  const { showToast } = useToast()
  const [selected, setSelected] = useState<CatalogItem | null>(null)

  // A corrupt collection loads empty; say so once instead of silently showing
  // the first-run empty state (FR-009).
  const [reportedCorrupt, setReportedCorrupt] = useState(false)
  if (favorites.corrupted && !reportedCorrupt) {
    setReportedCorrupt(true)
    showToast('بارگذاری علاقه‌مندی‌ها ناموفق بود؛ شروع دوباره', 'info')
  }

  const entries = favorites.ids
    .map((id) => ({ id, item: getCatalogItemById(id) }))
    .filter((e): e is { id: string; item: CatalogItem } => Boolean(e.item))

  const staleIds = favorites.ids.filter((id) => !entries.some((e) => e.id === id))
  const isEmpty = favorites.ids.length === 0

  return (
    <>
      <Header activePage="favorites" />

      <main id="main" className="wrap" style={{ paddingTop: 'calc(var(--hdr) + 34px)' }}>
        <section data-od-id="favorites-intro">
          <div className="eyebrow">
            <span className="pill-red">ذخیره‌شده در این دستگاه</span>
            <span className="pill-ghost">سند 010 · FR-004</span>
          </div>
          <h1
            style={{
              fontSize: 'clamp(30px, 4.6vw, 52px)',
              fontWeight: 800,
              letterSpacing: '-.025em',
              marginTop: '14px',
              lineHeight: 1.02,
            }}
          >
            علاقه‌مندی‌ها
          </h1>
          <p className="hero-desc" style={{ marginTop: '14px' }}>
            {isEmpty
              ? 'هنوز چیزی ذخیره نشده است.'
              : `${toFaDigits(favorites.ids.length)} مورد ذخیره شده، فقط در این مرورگر — بدون حساب کاربری، بدون نسخه روی سرور.`}
          </p>
        </section>

        {isEmpty ? (
          <div className="empty" style={{ marginTop: '28px' }}>
            <Heart className="w-12 h-12" />
            <strong>هنوز چیزی ذخیره نشده است</strong>
            <span>
              روی هر فیلم، بازی یا آلبوم — روی کارت یا بنر اصلی — روی قلب ضربه بزنید تا به این صفحه افزوده شود.
            </span>
            <Link className="btn btn-primary" href="/">
              مرور کاتالوگ
            </Link>
          </div>
        ) : (
          <>
            {GROUPS.map(({ key, label, Icon }) => {
              const items = entries.filter((e) => e.item.cat === key)
              if (items.length === 0) return null
              return (
                <section
                  key={key}
                  className="sec"
                  data-category={key}
                  style={{ marginTop: '32px' }}
                >
                  <div className="sec-head">
                    <h2>
                      <Icon
                        className="w-5 h-5"
                        style={{ verticalAlign: '-3px', marginInlineEnd: '8px' }}
                      />
                      {label}
                    </h2>
                    <span className="sub">{toFaDigits(items.length)} مورد ذخیره شده</span>
                  </div>
                  <div className="grid grid-6">
                    {items.map(({ id, item }) => (
                      <CatalogCard
                        key={id}
                        item={item}
                        onClick={() => setSelected(item)}
                        onToggleFavorite={favorites.toggle}
                        isItemFavorite={favorites.isLiked}
                      />
                    ))}
                  </div>
                </section>
              )
            })}

            {staleIds.length > 0 && (
              <section className="sec" style={{ marginTop: '32px' }}>
                <div className="sec-head">
                  <h2>ناموجود</h2>
                  <span className="sub">
                    {toFaDigits(staleIds.length)} مورد دیگر در کاتالوگ نیست
                  </span>
                </div>
                <p className="hero-desc" style={{ marginBottom: '12px' }}>
                  این شناسه‌های ذخیره‌شده دیگر در کاتالوگ نیستند، بنابراین چیزی برای نمایش وجود ندارد. حذف هرکدام، آن را برای همیشه پاک می‌کند.
                </p>
                <ul style={{ listStyle: 'none', display: 'grid', gap: '8px' }}>
                  {staleIds.map((id) => (
                    <li key={id} className="prov">
                      <span className="led warn"></span>
                      <strong style={{ color: '#e8e8e8' }}>{id}</strong>
                      <span>ناموجود</span>
                      <button
                        className="btn btn-ghost btn-sm"
                        type="button"
                        style={{ marginInlineStart: 'auto' }}
                        onClick={() => favorites.remove(id)}
                      >
                        <X className="w-3.5 h-3.5" />
                        <span>حذف</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {favorites.persistenceBlocked && (
              <div className="notice warn" style={{ marginTop: '28px' }}>
                <span className="led warn"></span>
                <span>
                  این مرورگر ذخیره‌سازی محلی را حفظ نمی‌کند، بنابراین علاقه‌مندی‌ها فقط برای این نشست هستند و پس از تازه‌سازی پاک می‌شوند.
                </span>
              </div>
            )}
          </>
        )}
      </main>

      <DetailDrawer
        item={selected}
        isOpen={Boolean(selected)}
        onClose={() => setSelected(null)}
        onToggleFavorite={favorites.toggle}
        isItemFavorite={favorites.isLiked}
        persistenceBlocked={favorites.persistenceBlocked}
      />

      <Footer />
    </>
  )
}
