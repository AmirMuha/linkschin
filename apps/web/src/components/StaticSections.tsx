'use client'

import React from 'react'
import Link from 'next/link'
import type { Category, MediaItem, SourceStatus } from '@/types/media'
import { toFaDigits } from '@/lib/format'
import { describeSource } from '@/components/SourceStatusBar'
import { MovieCard } from '@/components/cards/MovieCard'
import { GameCard } from '@/components/cards/GameCard'
import { MusicCard } from '@/components/cards/MusicCard'
import { ChevronDown } from 'lucide-react'

interface StaticSectionsProps {
  category: Category
  /** Live rows from GET /api/sources — never a hardcoded table. */
  sources: SourceStatus[]
  /** Fetched shelves; each renders nothing when empty. */
  trending: MediaItem[]
  latest: MediaItem[]
  onOpenDetails: (item: MediaItem) => void
  onToggleFavorite: (item: MediaItem) => void
  isItemFavorite: (id: string) => boolean
}

const FAQ_ITEMS = [
  {
    q: 'آیا این سرور فایلی را میزبانی یا پخش می‌کند؟',
    a: 'خیر. این تجمیع‌کننده فقط فراداده‌ها و نشانی‌های مستقیم منبع را پیدا می‌کند و آن‌ها را به مرورگر شما می‌دهد. ویدیو، صدا و آرشیوها مستقیماً بین دستگاه شما و CDN منبع جابه‌جا می‌شوند، بنابراین سرور هیچ پهنای باند رسانه‌ای مصرف نمی‌کند.',
  },
  {
    q: 'چرا یک نتیجه چند کیفیت دارد؟',
    a: 'هر فیلم به گزینه‌هایی تفکیک می‌شود که بر پایهٔ رزولوشن (۴۸۰ / ۷۲۰ / ۱۰۸۰ / 4K پیکسل)، کدک (x264، x265 / HEVC، ۱۰ بیتی) و صدای همراه (دوبلهٔ فارسی، زیرنویس نرم فارسی یا اصلی) دسته‌بندی شده‌اند. هر گزینه یک لینک مستقیم جداگانه است.',
  },
  {
    q: 'چرا در پارت‌های یک بازی، شماره‌ای جا افتاده است؟',
    a: 'بعضی پورتال‌ها پارت ۱، ۲ و ۴ را منتشر می‌کنند اما پارت ۳ را نه. پارت مفقود به‌جای شماره‌گذاری مجددِ پنهان، مشخص می‌شود تا نرم‌افزار دانلود نتواند آرام‌آرام آرشیوی ناقص بسازد.',
  },
  {
    q: 'می‌توانم فارسی جست‌وجو کنم؟',
    a: 'بله. پیش از خروج از سرور، عبارت جست‌وجو یکسان‌سازی می‌شود: ی و ک عربی به ی و ک فارسی تبدیل می‌شوند، ارقام عربی ٠-٩ به ارقام فارسی ۰-۹ تبدیل می‌شوند و نیم‌فاصله به‌عنوان فاصله در نظر گرفته می‌شود تا عبارت‌های ترکیبی هم پیدا شوند.',
  },
  {
    q: 'اگر یک منبع از کار بیفتد چه می‌شود؟',
    a: 'منابع سالم همچنان پاسخ می‌دهند و صفحه رندر می‌شود؛ فقط یک اعلان کم‌مزاحمت نام پورتال‌های در دسترس‌نبوده را نشان می‌دهد. منبعی که سه جست‌وجوی پیاپی در موسیقی شکست بخورد، ضعیف علامت‌گذاری و جایگزین می‌شود؛ منبعی که پنهان کنید از همهٔ جست‌وجوهای بعدی کنار گذاشته می‌شود.',
  },
  {
    q: 'آیا لینک‌های VIP یا نیازمند ورود هم بررسی می‌شوند؟',
    a: 'خیر. استخراج فقط روی لینک‌های عمومی و بدون نیاز به احراز هویت انجام می‌شود. لینک‌های پولی، لینک‌های نیازمند حساب کاربری و پخش‌کننده‌های محافظت‌شده با توکن نادیده گرفته می‌شوند، نه اینکه دور زده شوند.',
  },
]

const RESOLVE_STEPS = [
  {
    step: '۱ · یکسان‌سازی',
    desc: 'ی و ک عربی به ی و ک فارسی تبدیل می‌شوند، ارقام عربی به ارقام فارسی و نیم‌فاصله به فاصلهٔ معمولی تبدیل می‌شود تا عبارت جست‌وجوی ترکیبی هم پیدا شود.',
  },
  {
    step: '۲ · ارسال هم‌زمان',
    desc: 'همهٔ منابع فعال دستهٔ جاری هم‌زمان و زیر یک سقف زمانی کلی اجرا می‌شوند، بنابراین یک پورتال کند نمی‌تواند بارگذاری صفحه را متوقف کند.',
  },
  {
    step: '۳ · ادغام و رتبه‌بندی',
    desc: 'نتایج در یک فهرست رتبه‌بندی‌شده برای هر دسته ادغام می‌شوند. چیزی از مرز دسته‌ها عبور نمی‌کند — تنها دسته‌ای که در آن هستید جست‌وجو می‌شود.',
  },
  {
    step: '۴ · لینک مستقیم به شما',
    desc: 'کیفیت‌ها، پارت‌ها و سطح‌های بیت‌ریت به‌صورت نشانی منبع به مرورگر شما داده می‌شوند. خطر نامعتبر شدن توکن‌ها با کش ۳۰ تا ۶۰ دقیقه‌ای نتایج مدیریت می‌شود.',
  },
]

const LED: Record<'active' | 'degraded' | 'inactive', string> = {
  active: 'ok',
  degraded: 'warn',
  inactive: 'bad',
}

export function StaticSections({
  category,
  sources,
  trending,
  latest,
  onOpenDetails,
  onToggleFavorite,
  isItemFavorite,
}: StaticSectionsProps) {
  const trendTitle =
    category === 'movies'
      ? 'پربازدیدترین‌های امروز'
      : category === 'games'
        ? 'انتشارات پربازدید بازی'
        : 'قطعات پربازدید'

  const trendSub =
    category === 'music'
      ? 'کاور، خواننده و سطح‌های بیت‌ریت'
      : category === 'games'
        ? 'آرشیوهای چندپارتی با رمز استخراج'
        : 'امتیاز برگرفته از فرادادهٔ منبع'

  const latestTitle =
    category === 'movies'
      ? 'تازه‌ترین‌های امسال'
      : category === 'games'
        ? 'تازه فهرست‌شده'
        : 'انتشارات جدید'

  // One card renderer for every shelf: the same components the search grid uses.
  const renderCard = (item: MediaItem) => {
    if (item.category === 'games') {
      return (
        <GameCard
          key={item.id}
          item={item}
          onOpenDetails={onOpenDetails}
          onToggleFavorite={onToggleFavorite}
          isItemFavorite={isItemFavorite}
        />
      )
    }
    if (item.category === 'music') {
      return (
        <MusicCard
          key={item.id}
          item={item}
          onOpenDetails={onOpenDetails}
          onToggleFavorite={onToggleFavorite}
          isItemFavorite={isItemFavorite}
        />
      )
    }
    return (
      <MovieCard
        key={item.id}
        item={item}
        onOpenDetails={onOpenDetails}
        onToggleFavorite={onToggleFavorite}
        isItemFavorite={isItemFavorite}
      />
    )
  }

  // Live source health for the current category only.
  const catSources = sources.filter((s) => s.category === category)
  const described = catSources.map((s) => ({ s, status: describeSource(s).status }))
  const okCount = described.filter((d) => d.status === 'active').length
  const offSources = described.filter((d) => d.status === 'inactive')
  const ledStatus = described.some((d) => d.status === 'degraded') ? 'warn' : 'ok'

  return (
    <>
      {/* Health Strip — live rows only; no strip at all until the API answers. */}
      {catSources.length > 0 && (
        <div className="wrap">
          <div className="health" data-od-id="source-health" style={{ marginTop: '16px' }}>
            <span className={`led ${ledStatus}`}></span>
            <strong>
              {toFaDigits(okCount)} منبع از {toFaDigits(catSources.length)} منبع پاسخ دادند
            </strong>
            <ul>
              {described.map(({ s, status }) => (
                <li key={s.id} className="chip">
                  <span className={`led ${LED[status]}`}></span>
                  <span>{s.name}</span>
                  <span style={{ color: 'var(--muted-2)' }}>
                    {status === 'active' ? 'فعال' : status === 'degraded' ? 'افت کیفیت' : 'غیرفعال'}
                  </span>
                </li>
              ))}
            </ul>
            {offSources.length > 0 && (
              <span style={{ color: 'var(--muted-2)', fontSize: '12px' }}>
                در دسترس نیست: {offSources.map(({ s }) => s.name).join('، ')}
              </span>
            )}
            <Link className="btn btn-quiet btn-sm" href="/sources">
              مدیریت منابع
            </Link>
          </div>
        </div>
      )}

      {/* Trending Section */}
      {trending.length > 0 && (
        <section className="wrap sec" data-od-id="section-trending" id="trending">
          <div className="sec-head">
            <h2 id="trendTitle">{trendTitle}</h2>
            <span className="sub" id="trendSub">
              {trendSub}
            </span>
          </div>
          <div className="grid grid-6" id="trendGrid">
            {trending.map(renderCard)}
          </div>
        </section>
      )}

      {/* Latest Shelf Section */}
      {latest.length > 0 && (
        <section className="wrap sec" data-od-id="section-latest" id="latest">
          <div className="sec-head">
            <h2 id="latestTitle">{latestTitle}</h2>
            <span className="sub">مرتب‌شده بر اساس تاریخ انتشار</span>
          </div>
          <div className="shelf no-sb" id="latestShelf">
            {latest.map(renderCard)}
          </div>
        </section>
      )}

      {/* Why Section */}
      <section className="wrap sec" data-od-id="section-why" id="why">
        <div className="notice" style={{ marginBottom: '20px' }}>
          <span className="led ok"></span>
          <span>
            <strong style={{ color: '#fff' }}>هیچ رسانه‌ای بازپخش نمی‌شود.</strong> این سرور فقط
            لینک‌ها و فراداده‌ها را پیدا می‌کند. هر دانلود و پیش‌نمایش مستقیماً از مرورگر شما به
            CDN منبع وصل می‌شود — سایت هیچ ویدیو، صدا یا آرشیوی را ذخیره، میزبانی یا پروکسی
            نمی‌کند. تنها استثنای اعلام‌شده ابزار YouTube به MP3 است.
          </span>
        </div>
        <div className="sec-head">
          <h2>یک جست‌وجو چگونه پردازش می‌شود</h2>
          <span className="sub">محدود به دسته‌ای که در آن هستید</span>
        </div>
        <div
          className="grid"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))' }}
          id="flowGrid"
        >
          {RESOLVE_STEPS.map((step, idx) => (
            <div
              key={idx}
              className="notice"
              style={{
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '8px',
              }}
            >
              <strong
                style={{
                  color: '#fff',
                  fontSize: '13px',
                  letterSpacing: '.1em',
                  textTransform: 'uppercase',
                }}
              >
                {step.step}
              </strong>
              <span>{step.desc}</span>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ Section */}
      <section className="wrap sec" data-od-id="section-faq" id="faq">
        <div
          className="sec-head"
          style={{
            justifyContent: 'center',
            textAlign: 'center',
            display: 'block',
            border: 0,
          }}
        >
          <h2 style={{ color: 'var(--accent)' }}>مرکز پشتیبانی</h2>
          <p
            style={{
              marginTop: '10px',
              color: 'var(--muted)',
              fontSize: 'clamp(15px, 1.4vw, 18px)',
            }}
          >
            پرسش‌های پرتکرار دربارهٔ لینک‌های مستقیم، کش‌ها و فیلترکردن محتوای سانسورشده.
          </p>
        </div>
        <div className="faq" id="faqList">
          {FAQ_ITEMS.map((item, idx) => (
            <details key={idx} className="q">
              <summary>
                <span>{item.q}</span>
                <span className="caret">
                  <ChevronDown className="w-4 h-4" />
                </span>
              </summary>
              <p>{item.a}</p>
            </details>
          ))}
        </div>
      </section>
    </>
  )
}
