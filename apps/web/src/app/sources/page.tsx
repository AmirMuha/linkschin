'use client'

import React, { useState, useEffect } from 'react'
import { Header } from '@/components/Header'
import { Footer } from '@/components/Footer'
import { useToast } from '@/components/ui/ToastNotification'
import { toFaDigits } from '@/lib/format'
import {
  fetchSources,
  updateSourceAddress,
  toggleSourceEnabled,
  submitSourceSuggestion,
} from '@/lib/api'

/** One registry row: the display shape the table edits, filled from /api/sources. */
interface SourceRow {
  id: string
  name: string
  cat: 'movies' | 'games' | 'music'
  tier: 1 | 2 | 3
  tierLabel: string
  notes: string
  baseUrl: string
  mirrorUrl: string
  enabled: boolean
  state: 'ok' | 'warn' | 'bad'
}

/** Display copy for the expansion goal — live counts come from the API. */
const EXPANSION_TARGETS = { movies: 20, games: 8, music: 20 } as const

export default function SourcesPage() {
  const { showToast } = useToast()
  const [sources, setSources] = useState<SourceRow[]>([])
  const [hidden, setHidden] = useState<Record<string, boolean>>({})

  // Fetch live sources from backend
  useEffect(() => {
    fetchSources().then((live) => {
      if (live && live.length > 0) {
        setSources(
          live.map((s) => ({
            id: s.id,
            name: s.name,
            cat: s.category as SourceRow['cat'],
            tier: (s.access_tier === 'premium' ? 2 : (s.access_tier === 'freemium' ? 3 : 1)) as 1 | 2 | 3,
            tierLabel: s.access_tier ? `سطح ${toFaDigits(s.access_tier)}` : 'سطح ۱',
            notes: s.inactive_reason || s.status || '',
            baseUrl: s.base_url || '',
            mirrorUrl: (s as { mirror_url?: string }).mirror_url || '',
            enabled: s.enabled,
            state: s.status === 'active' ? 'ok' : (s.status === 'degraded' ? 'warn' : 'bad'),
          }))
        )
      }
    }).catch(() => {})
  }, [])

  // Suggestion form state
  const [url, setUrl] = useState('')
  const [category, setCategory] = useState<'movies' | 'games' | 'music'>('movies')
  const [name, setName] = useState('')
  const [tier, setTier] = useState('1')
  const [lang, setLang] = useState('EN')
  const [contact, setContact] = useState('')
  const [notes, setNotes] = useState('')
  const [agreed, setAgreed] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  // Toggle enabled
  function handleToggleEnabled(id: string) {
    setSources((prev) =>
      prev.map((s) => {
        if (s.id !== id) return s
        const next = !s.enabled
        toggleSourceEnabled(id, next).catch(() => {})
        showToast(
          `${s.name} ${next ? 'فعال شد — در موج بعدی جستجو شرکت می‌کند' : 'غیرفعال شد — از همهٔ جستجوها کنار گذاشته می‌شود'}`
        )
        return { ...s, enabled: next }
      })
    )
  }

  // Toggle hidden for me
  function handleToggleHide(id: string) {
    const s = sources.find((x) => x.id === id)
    setHidden((prev) => {
      const next = !prev[id]
      showToast(
        next
          ? `${s?.name || id} پنهان شد — همهٔ جستجوهای بعدی روی این دستگاه آن را رد می‌کنند`
          : `${s?.name || id} بازگردانده شد`
      )
      return { ...prev, [id]: next }
    })
  }

  // Address change
  function handleAddressChange(id: string, type: 'base' | 'mirror', val: string) {
    const s = sources.find((x) => x.id === id)
    if (val.trim() && !/^https:\/\//i.test(val.trim())) {
      showToast('آدرس باید با https:// شروع شود', 'error')
      return
    }
    updateSourceAddress(id, type === 'base' ? val : undefined, type === 'mirror' ? val : undefined).catch(() => {})
    setSources((prev) =>
      prev.map((item) => {
        if (item.id !== id) return item
        return type === 'base'
          ? { ...item, baseUrl: val }
          : { ...item, mirrorUrl: val }
      })
    )
    showToast(
      `${s?.name || id}: آدرس ${type === 'base' ? 'اصلی' : 'پشتیبان'} ذخیره شد. تنها پیکربندی — نیازی به تغییر کد نیست (FR-021).`
    )
  }

  // Submit suggestion
  function handleSubmitSuggestion(e: React.FormEvent) {
    e.preventDefault()
    const errs: Record<string, string> = {}

    if (!url.trim()) {
      errs.url = 'آدرس پورتال را بچسبانید'
    } else {
      try {
        const u = new URL(url.trim())
        if (u.protocol !== 'https:' && u.protocol !== 'http:') {
          errs.url = 'باید یک آدرس HTTP(S) باشد'
        }
      } catch {
        errs.url = 'آدرس معتبر نیست'
      }
    }

    if (!name.trim()) {
      errs.name = 'پورتال خود را با چه نامی معرفی می‌کند؟'
    }

    if (contact.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact.trim())) {
      errs.contact = 'ایمیل معتبر نیست'
    }

    if (!agreed) {
      errs.agreed = 'باید سیاست لینک‌های بدون احراز هویت را تأیید کنید'
    }

    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }

    setErrors({})
    submitSourceSuggestion({
      url: url.trim(),
      category,
      source_name: name.trim(),
      proposed_tier: tier,
      default_audio_track: lang,
      contact: contact.trim() || undefined,
      notes: notes.trim() || undefined,
    }).then((res) => {
      showToast(`«${name.trim()}» به صف بررسی اپراتور ارسال شد (دامنه: ${res.domain}، درخواست‌ها: ${toFaDigits(res.request_count)}).`)
    }).catch((err) => {
      showToast(err.message || `«${name.trim()}» به صف بررسی اپراتور ارسال شد.`)
    })

    // Reset form
    setUrl('')
    setName('')
    setContact('')
    setNotes('')
    setAgreed(false)
  }

  function handleClearForm() {
    setUrl('')
    setName('')
    setContact('')
    setNotes('')
    setAgreed(false)
    setErrors({})
    showToast('فرم پاک شد')
  }

  const enabledCount = sources.filter((s) => s.enabled).length

  return (
    <>
      <Header activePage="sources" />

      <main id="main" className="wrap" style={{ paddingTop: 'calc(var(--hdr) + 34px)' }}>
        {/* Intro */}
        <section data-od-id="sources-intro">
          <div className="eyebrow">
            <span className="pill-red">کنسول اپراتور</span>
            <span className="pill-ghost">سند 001 · US5 · FR-021 · 004 · 007</span>
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
            رجیستری منابع
          </h1>
          <p className="hero-desc" style={{ marginTop: '14px' }}>
            هر پورتال یک ماژول مستقل پشت یک رابط واحد برای جستجو و استخراج است. افزودن یک منبع یعنی
            نوشتن یک ماژول جدید و اضافه‌شدن یک ردیف به همین جدول — جستجو، رتبه‌بندی و رابط کاربری
            دست‌نخورده باقی می‌مانند. جابه‌جایی دامنه با دنبال‌کردن ریدایرکت‌های ۳۰۱/۳۰۲ مدیریت
            می‌شود و آدرس پایه در پیکربندی نگهداری می‌گردد، بنابراین تغییر آینه هرگز نیاز به تغییر
            کد ندارد.
          </p>
        </section>

        {/* Expansion Status */}
        <section className="sec" data-od-id="expansion-status">
          <div className="sec-head">
            <h2>وضعیت توسعه</h2>
            <span className="sub">سند 005 · 006 — درخواست ۲۰ پورتال برای هر نوع رسانه</span>
          </div>
          <div
            className="grid"
            style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}
            id="expansion"
          >
            {(['movies', 'games', 'music'] as const).map((catKey) => {
              // Live count from the fetched registry; the target is display copy.
              const live = sources.filter((s) => s.cat === catKey && s.enabled).length
              const target = EXPANSION_TARGETS[catKey]
              const pct = Math.min(100, Math.round((live / target) * 100))
              const label =
                catKey === 'movies'
                  ? 'پورتال فیلم و سریال'
                  : catKey === 'games'
                    ? 'پورتال بازی'
                    : 'پورتال موسیقی'

              return (
                <div
                  key={catKey}
                  className="notice"
                  style={{
                    flexDirection: 'column',
                    alignItems: 'stretch',
                    gap: '10px',
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
                    {label}
                  </strong>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                    <span style={{ fontSize: '26px', fontWeight: 800 }}>
                      {toFaDigits(live)}
                    </span>
                    <span style={{ color: 'var(--muted-2)' }}>
                      از {toFaDigits(target)} پورتال فعال
                    </span>
                  </div>
                  <div className="bar">
                    <i style={{ width: `${pct}%` }}></i>
                  </div>
                  <span style={{ fontSize: '12px', color: 'var(--muted)' }}>
                    {toFaDigits(Math.max(0, target - live))} پورتال دیگر باقی‌مانده — آن‌ها را در فرم پایین ثبت کنید.
                  </span>
                </div>
              )
            })}
          </div>
        </section>

        {/* Registry Table */}
        <section className="sec" data-od-id="registry-table">
          <div className="sec-head">
            <h2>منابع ثبت‌شده</h2>
            <span className="sub" id="regCount">
              {toFaDigits(sources.length)} منبع · {toFaDigits(enabledCount)} فعال
            </span>
          </div>
          <div className="tbl-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>منبع</th>
                  <th>دسته</th>
                  <th>سطح</th>
                  <th>سلامت</th>
                  <th>آدرس اصلی</th>
                  <th>آینه پشتیبان</th>
                  <th>فعال</th>
                  <th>پنهان برای من</th>
                </tr>
              </thead>
              <tbody id="regBody">
                {sources.map((s) => {
                  const isOff = !s.enabled
                  const stateKey = isOff ? 'off' : s.state
                  const ledClass =
                    stateKey === 'off'
                      ? 'bad'
                      : stateKey === 'warn'
                        ? 'warn'
                        : stateKey === 'ok'
                          ? 'ok'
                          : 'bad'
                  const stateLabel =
                    stateKey === 'off'
                      ? 'غیرفعال'
                      : stateKey === 'warn'
                        ? 'دارای اختلال'
                        : stateKey === 'ok'
                          ? 'پاسخگو'
                          : 'خطا'
                  const catLabel =
                    s.cat === 'movies'
                      ? 'فیلم و سریال'
                      : s.cat === 'games'
                        ? 'بازی'
                        : 'موسیقی'

                  return (
                    <tr key={s.id}>
                      <td>
                        <strong>{s.name}</strong>
                        <br />
                        <span style={{ color: 'var(--muted-2)', fontSize: '12px' }}>
                          {s.notes}
                        </span>
                      </td>
                      <td>{catLabel}</td>
                      <td>
                        <span className="pill-ghost">{s.tierLabel}</span>
                      </td>
                      <td>
                        <span className="state">
                          <span className={`led ${ledClass}`}></span>
                          {stateLabel}
                        </span>
                      </td>
                      <td>
                        <input
                          className="input"
                          style={{
                            minHeight: '44px',
                            padding: '8px 12px',
                            fontSize: '13px',
                          }}
                          dir="ltr"
                          defaultValue={s.baseUrl || ''}
                          placeholder="https://live-mirror…"
                          onBlur={(e) => handleAddressChange(s.id, 'base', e.target.value)}
                          aria-label={`آدرس اصلی ${s.name}`}
                        />
                      </td>
                      <td>
                        <input
                          className="input"
                          style={{
                            minHeight: '44px',
                            padding: '8px 12px',
                            fontSize: '13px',
                          }}
                          dir="ltr"
                          defaultValue={s.mirrorUrl || ''}
                          placeholder="https://fallback…"
                          onBlur={(e) => handleAddressChange(s.id, 'mirror', e.target.value)}
                          aria-label={`آینه پشتیبان ${s.name}`}
                        />
                      </td>
                      <td>
                        <label className="switch">
                          <input
                            type="checkbox"
                            checked={s.enabled}
                            onChange={() => handleToggleEnabled(s.id)}
                          />
                          <span className="track"></span>
                          <span className="sr">فعال‌کردن {s.name}</span>
                        </label>
                      </td>
                      <td>
                        <label className="switch">
                          <input
                            type="checkbox"
                            checked={Boolean(hidden[s.id])}
                            onChange={() => handleToggleHide(s.id)}
                          />
                          <span className="track"></span>
                          <span className="sr">پنهان‌کردن {s.name} از نتایج من</span>
                        </label>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <p
            style={{
              marginTop: '14px',
              color: 'var(--muted-2)',
              fontSize: '12px',
              maxWidth: '80ch',
            }}
          >
            آدرس‌ها عمداً خالی گذاشته شده‌اند: دامنه پورتال‌ها سریع‌تر از آن دست‌آخوردنی است که یک نسخهٔ
            پیکربندی بتواند با آن همگام بماند. اسکرپر ریدایرکت‌های ۳۰۱/۳۰۲ را دنبال می‌کند و دامنهٔ
            فعال را هنگام درخواست ثبت می‌کند، بنابراین آینهٔ فعلی را در «آدرس اصلی» و یک آینهٔ پشتیبانِ
            سالم را در «آینه پشتیبان» وارد کنید.
          </p>
        </section>

        {/* Suggest a source */}
        <section className="sec" data-od-id="suggest" id="suggest">
          <div className="sec-head">
            <h2>پیشنهاد منبع جدید</h2>
            <span className="sub">سند 004 — صف بررسی اپراتور</span>
          </div>
          <form
            className="grid"
            style={{
              gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
              gap: '18px',
            }}
            id="suggestForm"
            onSubmit={handleSubmitSuggestion}
            noValidate
          >
            <div className={`field ${errors.url ? 'invalid' : ''}`} data-field="url">
              <label htmlFor="f-url">آدرس پورتال</label>
              <input
                className="input"
                id="f-url"
                type="url"
                placeholder="https://example-portal.ir"
                dir="ltr"
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value)
                  if (errors.url) setErrors((prev) => ({ ...prev, url: '' }))
                }}
              />
              <span className="err" id="e-url">
                {errors.url}
              </span>
            </div>

            <div className="field" data-field="cat">
              <label htmlFor="f-cat">دسته</label>
              <select
                className="select"
                id="f-cat"
                value={category}
                onChange={(e) =>
                  setCategory(e.target.value as 'movies' | 'games' | 'music')
                }
              >
                <option value="movies">فیلم و سریال</option>
                <option value="games">بازی</option>
                <option value="music">موسیقی</option>
              </select>
              <span className="hint">
                ماژول اسکرپر تنها برای دسته‌هایی که انتخاب می‌کنید ساخته می‌شود.
              </span>
            </div>

            <div className={`field ${errors.name ? 'invalid' : ''}`} data-field="name">
              <label htmlFor="f-name">نام پورتال</label>
              <input
                className="input"
                id="f-name"
                type="text"
                placeholder="نامی که پورتال خود را با آن معرفی می‌کند"
                value={name}
                onChange={(e) => {
                  setName(e.target.value)
                  if (errors.name) setErrors((prev) => ({ ...prev, name: '' }))
                }}
              />
              <span className="err" id="e-name">
                {errors.name}
              </span>
            </div>

            <div className="field" data-field="tier">
              <label htmlFor="f-tier">سطح پیشنهادی</label>
              <select
                className="select"
                id="f-tier"
                value={tier}
                onChange={(e) => setTier(e.target.value)}
              >
                <option value="1">سطح ۱ — اصلی</option>
                <option value="2">سطح ۲ — پشتیبان</option>
                <option value="3">سطح ۳ — آزمایشی</option>
              </select>
              <span className="hint">
                سطح، اولویت ادغام و اینکه هنگام افت یک دسته کدام منابع باقی بمانند را تعیین می‌کند.
              </span>
            </div>

            <div className="field" data-field="lang">
              <label htmlFor="f-lang">صدای پیش‌فرض</label>
              <select
                className="select"
                id="f-lang"
                value={lang}
                onChange={(e) => setLang(e.target.value)}
              >
                <option value="EN">اصلی</option>
                <option value="FA-DUB">دوبله فارسی</option>
                <option value="FA-SUB">زیرنویس فارسی</option>
              </select>
            </div>

            <div className={`field ${errors.contact ? 'invalid' : ''}`} data-field="contact">
              <label htmlFor="f-contact">راه تماس (اختیاری)</label>
              <input
                className="input"
                id="f-contact"
                type="email"
                placeholder="you@example.com"
                dir="ltr"
                value={contact}
                onChange={(e) => {
                  setContact(e.target.value)
                  if (errors.contact) setErrors((prev) => ({ ...prev, contact: '' }))
                }}
              />
              <span className="err" id="e-contact">
                {errors.contact}
              </span>
            </div>

            <div className="field" data-field="notes" style={{ gridColumn: '1 / -1' }}>
              <label htmlFor="f-notes">چه چیزی ارائه می‌دهد؟</label>
              <textarea
                className="textarea"
                id="f-notes"
                placeholder="لینک مستقیم؟ آرشیو چندبخشی؟ سطح بیت‌ریت؟ قرارداد رمز عبور خاصی دارد؟"
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              ></textarea>
              <span className="err" id="e-notes"></span>
            </div>

            <div
              className={`field ${errors.agreed ? 'invalid' : ''}`}
              style={{ gridColumn: '1 / -1' }}
            >
              <label className="switch">
                <input
                  type="checkbox"
                  id="f-ok"
                  checked={agreed}
                  onChange={(e) => {
                    setAgreed(e.target.checked)
                    if (errors.agreed) setErrors((prev) => ({ ...prev, agreed: '' }))
                  }}
                />
                <span className="track"></span>
                <span
                  style={{
                    fontSize: '13px',
                    textTransform: 'none',
                    letterSpacing: 0,
                    color: 'var(--muted)',
                  }}
                >
                  درک می‌کنم که این تجمیع‌کننده تنها لینک‌های عمومی و بدون احراز هویت را نمایه می‌کند و هرگز
                  از دیوار پولی یا صفحهٔ ورود عبور نمی‌کند.
                </span>
              </label>
              {errors.agreed && <span className="err">{errors.agreed}</span>}
            </div>

            <div
              style={{
                gridColumn: '1 / -1',
                display: 'flex',
                gap: '12px',
                flexWrap: 'wrap',
                alignItems: 'center',
              }}
            >
              <button className="btn btn-primary" type="submit">
                ارسال به صف بررسی
              </button>
              <button
                className="btn btn-quiet"
                type="button"
                id="resetForm"
                onClick={handleClearForm}
              >
                پاک‌کردن
              </button>
              <span className="hint" style={{ color: 'var(--muted-2)' }}>
                پورتال‌های ارسال‌شده وارد صف اپراتور می‌شوند و تا زمانی که ماژول اسکرپرشان ساخته نشود و
                این جدول ردیف تازه‌ای نگیرد، در هیچ جستجویی ظاهر نمی‌شوند.
              </span>
            </div>
          </form>
        </section>

        {/* Tiers, censorship and IMDb */}
        <section className="sec" data-od-id="source-faq">
          <div className="sec-head">
            <h2>سطوح، سانسور و امتیاز IMDb</h2>
            <span className="sub">سند 007</span>
          </div>
          <div
            className="grid"
            style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}
          >
            <div
              className="notice"
              style={{
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '8px',
              }}
            >
              <strong style={{ color: '#fff' }}>سطح ۱ — اصلی</strong>
              <span>
                بالاترین اولویت در ادغام. وقتی منبع سطح ۱ پاسخ می‌دهد، سطح ۳ اصلاً پرسیده نمی‌شود.
              </span>
            </div>
            <div
              className="notice"
              style={{
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '8px',
              }}
            >
              <strong style={{ color: '#fff' }}>سطح ۲ — پشتیبان</strong>
              <span>
                در همان موج پرس‌وجو بررسی می‌شود اما رتبه‌ای پایین‌تر از سطح ۱ دارد. وقتی سطح ۱ دچار
                افت می‌شود، عمدهٔ کاتالوگ را همین سطح پوشش می‌دهد.
              </span>
            </div>
            <div
              className="notice"
              style={{
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '8px',
              }}
            >
              <strong style={{ color: '#fff' }}>سطح ۳ — آزمایشی</strong>
              <span>
                تنها زمانی پرسیده می‌شود که سطح‌های ۱ و ۲ هیچ نتیجه‌ای برای این پرس‌وجو برنگردانند.
              </span>
            </div>
          </div>
          <div className="tbl-wrap" style={{ marginTop: '18px' }}>
            <table className="data">
              <thead>
                <tr>
                  <th>فیلتر</th>
                  <th>پیش‌فرض</th>
                  <th>اثر روی نتایج</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>کف امتیاز IMDb</td>
                  <td className="mono">0.0</td>
                  <td>
                    هر چیزی زیر این کف کم‌رنگ شده و در انتهای فهرست مرتب می‌شود؛ خودِ امتیاز هرگز پنهان
                    نمی‌شود.
                  </td>
                </tr>
                <tr>
                  <td>سانسور</td>
                  <td className="mono">شامل</td>
                  <td>
                    با انتخاب <em>فقط نسخهٔ بدون سانسور</em>، انتشارهایی که به‌عنوان نسخهٔ سانسورشده
                    علامت خورده‌اند کنار گذاشته می‌شوند؛ یا با <em>حذف سانسورشده‌ها</em> کاملاً از نتایج
                    کنار گذاشته می‌شوند.
                  </td>
                </tr>
                <tr>
                  <td>سطح منبع</td>
                  <td className="mono">۱–۳</td>
                  <td>
                    بالا بردن سقف به سطح ۱، تأخیر را کم می‌کند و منابع پشتیبانی را که فقط فهرست را
                    پر می‌کردند پنهان می‌سازد.
                  </td>
                </tr>
                <tr>
                  <td>پنهان‌سازی برای هر کاربر</td>
                  <td className="mono">خاموش</td>
                  <td>
                    منبع پنهان‌شده از همهٔ جستجوهای بعدی روی این دستگاه کنار گذاشته می‌شود، نه فقط از
                    جستجوی فعلی.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* Content Policy */}
        <section className="sec" data-od-id="legal" id="legal">
          <div className="sec-head">
            <h2>سیاست محتوا</h2>
            <span className="sub">این نمونهٔ اولیه چه کاری انجام می‌دهد و چه کاری نمی‌کند</span>
          </div>
          <div
            className="grid"
            style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}
          >
            <div
              className="notice"
              style={{
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '8px',
              }}
            >
              <strong style={{ color: '#fff' }}>پیاده‌سازی‌شده در رابط کاربری</strong>
              <span>
                جداسازی دسته‌ها، نرمال‌سازی فارسی/عربی، دسته‌بندی فرمت‌ها، فهرست آرشیو چندبخشی همراه با
                تشخیص بخش‌های جاافتاده، کپی رمز عبور، سطوح بیت‌ریت، سلامت منابع، فیلتر سطح، دستیار و همین
                صف بررسی.
              </span>
            </div>
            <div
              className="notice"
              style={{
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '8px',
              }}
            >
              <strong style={{ color: '#fff' }}>پیاده‌سازی‌نشده در اینجا</strong>
              <span>
                هیچ ماژول اسکرپری، هیچ درخواست HTTP به پورتالی، هیچ خزید زمان‌بندی‌شده و هیچ ذخیرهٔ کشی
                وجود ندارد. دکمه‌های دانلود به آدرس بالادستی که می‌توانستند باز کنند اشاره می‌کنند و همین
                را اعلام می‌کنند.
              </span>
            </div>
            <div
              className="notice"
              style={{
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '8px',
              }}
            >
              <strong style={{ color: '#fff' }}>مسئولیت اپراتور</strong>
              <span>
                راه‌اندازی نمایه‌سازهای زنده روی پورتال‌های شخص‌ثالث تصمیمی جداگانه با بازبینی حقوقی و
                شرایط استفادهٔ خودش است. این مخزن در همین‌جا، روی رابط کاربری، متوقف می‌شود.
              </span>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </>
  )
}
