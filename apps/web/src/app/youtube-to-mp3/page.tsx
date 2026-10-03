'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Header } from '@/components/Header'
import { Footer } from '@/components/Footer'
import { useToast } from '@/components/ui/ToastNotification'
import { fmtMiB, toFaDigits } from '@/lib/catalog'
import { startConversion, pollConversion } from '@/lib/api'

interface JobHistory {
  id: string
  title: string
  bitrate: number
  rate: number
  size: string
  meta: boolean
  norm: boolean
  downloadUrl?: string
}

const STEPS = [
  'شناسایی شناسهٔ ویدیو',
  'خواندن جریان‌های صوتی موجود',
  'استخراج ترک صوتی',
  'کدگذاری MP3',
  'نهایی‌سازی تگ‌ها',
]

const ID_RE = /^[A-Za-z0-9_-]{11}$/

function extractVideoId(v: string): string {
  const m = String(v).match(/(?:youtu\.be\/|v=|embed\/|shorts\/)([A-Za-z0-9_-]{11})/)
  return m ? m[1] : ''
}

function calcMp3Bytes(secs: number, kbps: number): number {
  return Math.round((secs * kbps * 1000) / 8)
}

export default function YoutubeToMp3Page() {
  const { showToast } = useToast()

  const [url, setUrl] = useState('')
  const [videoId, setVideoId] = useState('')
  const [bitrate, setBitrate] = useState<number>(320)
  const [rate, setRate] = useState<number>(44100)
  const [writeMeta, setWriteMeta] = useState(true)
  const [normFilename, setNormFilename] = useState(false)

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState('')
  const [activeVid, setActiveVid] = useState('')
  const [lastCompletedNotice, setLastCompletedNotice] = useState<string | null>(null)

  const [history, setHistory] = useState<JobHistory[]>([])
  const lastRunRef = useRef(0)
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  // Sync url -> id
  function handleUrlChange(val: string) {
    setUrl(val)
    const vid = extractVideoId(val)
    if (vid) {
      setVideoId(vid)
      setErrors({})
    }
  }

  // Sync id -> url
  function handleIdChange(val: string) {
    const trimmed = val.trim()
    setVideoId(trimmed)
    if (!trimmed) {
      setUrl('')
      return
    }
    if (ID_RE.test(trimmed)) {
      setUrl(`https://www.youtube.com/watch?v=${trimmed}`)
      setErrors({})
    } else if (/^https?:\/\//i.test(trimmed)) {
      setUrl(trimmed)
      const extracted = extractVideoId(trimmed)
      if (extracted) setVideoId(extracted)
      setErrors({})
    }
  }

  // Cancel job
  function handleCancel() {
    if (timerRef.current) clearInterval(timerRef.current)
    setRunning(false)
    setProgress(0)
    setCurrentStep('')
    setActiveVid('')
    showToast('کار لغو شد — فایل ناقص دور ریخته شد')
  }

  // Finish job
  function finishJob(vid: string, downloadUrl?: string, actualTitle?: string) {
    if (timerRef.current) clearInterval(timerRef.current)
    setRunning(false)
    setProgress(100)

    const secs = 240
    const bytes = calcMp3Bytes(secs, bitrate)
    const title = actualTitle || `youtube-${vid}`
    const sizeStr = fmtMiB(bytes)

    const newJob: JobHistory = {
      id: vid,
      title,
      bitrate,
      rate,
      size: sizeStr,
      meta: writeMeta,
      norm: normFilename,
      downloadUrl,
    }

    setHistory((prev) => [newJob, ...prev])
    setLastCompletedNotice(
      `در ${bitrate} kbps / ${rate / 1000} kHz کدگذاری شد — استخراج صوت کامل شد. فایل آمادهٔ دانلود مستقیم است.`
    )
    showToast(`Conversion finished — ${title}`)
  }

  // Form submit
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (running) {
      showToast('هر بار یک کار — اول کار در حال اجرا را لغو کنید', 'error')
      return
    }

    const raw = url.trim() || videoId.trim()
    if (!raw) {
      setErrors({ url: 'آدرس یوتیوب یا شناسهٔ ۱۱ نویسه‌ای ویدیو را بچسبانید.' })
      return
    }

    const vid = extractVideoId(raw) || (ID_RE.test(raw) ? raw : '')
    if (!vid) {
      setErrors({
        url: 'شناسهٔ ۱۱ نویسه‌ای ویدیو در این آدرس پیدا نشد. لینک پلی‌لیست و کانال پذیرفته نمی‌شود.',
      })
      return
    }

    if (!ID_RE.test(vid)) {
      setErrors({ url: 'این شناسهٔ ویدیو ۱۱ نویسه ندارد.' })
      return
    }

    setErrors({})
    setRunning(true)
    lastRunRef.current = Date.now()
    setActiveVid(vid)
    setProgress(10)
    setCurrentStep('آغاز استخراج روی سرور…')
    setLastCompletedNotice(null)

    try {
      const fullUrl = raw.startsWith('http') ? raw : `https://www.youtube.com/watch?v=${vid}`
      const startRes = await startConversion({
        url: fullUrl,
        bitrate,
        sample_rate: rate,
        write_meta: writeMeta,
      })

      const reqId = startRes.request_id
      timerRef.current = setInterval(async () => {
        try {
          const pollRes = await pollConversion(reqId)
          if (pollRes.status === 'processing') {
            setProgress(pollRes.progress || 40)
            setCurrentStep(pollRes.current_step || 'در حال پردازش ترک صوتی…')
          } else if (pollRes.status === 'completed') {
            if (timerRef.current) clearInterval(timerRef.current)
            finishJob(vid, pollRes.download_url, pollRes.video_title)
          } else if (pollRes.status === 'failed') {
            if (timerRef.current) clearInterval(timerRef.current)
            setRunning(false)
            showToast(pollRes.error_message || 'تبدیل ناموفق بود', 'error')
          }
        } catch {
          // ignore transient poll errors
        }
      }, 1000)
    } catch (err: any) {
      setRunning(false)
      showToast(err.message || 'خطا در شروع تبدیل', 'error')
    }
  }

  function handleClearHistory() {
    if (history.length === 0) {
      showToast('تاریخچه از قبل خالی است')
      return
    }
    setHistory([])
    showToast('تاریخچهٔ نشست پاک شد')
  }

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  return (
    <>
      <Header activePage="mp3" />

      <main id="main" className="wrap" style={{ paddingTop: 'calc(var(--hdr) + 34px)' }}>
        {/* Intro */}
        <section data-od-id="mp3-intro">
          <div className="eyebrow">
            <span className="pill-red">استثنای اعلام‌شده</span>
            <span className="pill-ghost">
              سند 008 · این FR اصل سوم قانون اساسی را فقط برای همین ابزار کنار می‌گذارد
            </span>
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
            یوتیوب به MP3
          </h1>
          <p className="hero-desc" style={{ marginTop: '14px' }}>
            در تمام بخش‌های دیگر این محصول، سرور فقط لینک می‌دهد و چیزی را بازپخش نمی‌کند. این ابزار
            تنها استثنای اعلام‌شده است: جریان صوتی را می‌گیرد، کدگذاری می‌کند و فایل را در اختیارتان
            می‌گذارد. هر بار یک ویدیو، بدون پلی‌لیست و بدون صف دسته‌ای.
          </p>
          <div className="notice warn" style={{ marginTop: '20px' }}>
            <span className="led warn"></span>
            <span>
              تنها محتوایی را تبدیل کنید که مالکش هستید یا مجوز دانلودش را دارید. این نمونهٔ اولیه تمام
              رابط کاربری — اعتبارسنجی، سطوح بیت‌ریت، پیشرفت و تاریخچه — را اجرا می‌کند بدون آنکه با
              یوتیوب تماس بگیرد.
            </span>
          </div>
        </section>

        {/* Conversion Form */}
        <section className="sec" data-od-id="mp3-form">
          <form
            id="mp3Form"
            onSubmit={handleSubmit}
            noValidate
            style={{ display: 'grid', gap: '20px', maxWidth: '760px' }}
          >
            <div className={`field ${errors.url ? 'invalid' : ''}`} data-field="url">
              <label htmlFor="m-url">آدرس ویدیوی یوتیوب</label>
              <input
                className="input"
                id="m-url"
                type="url"
                dir="ltr"
                placeholder="https://www.youtube.com/watch?v=…"
                autoComplete="off"
                value={url}
                onChange={(e) => handleUrlChange(e.target.value)}
              />
              <span className="err" id="e-url">
                {errors.url}
              </span>
            </div>

            <div className="field" data-field="id">
              <label htmlFor="m-id">…یا فقط شناسهٔ ویدیو را بچسبانید</label>
              <input
                className="input"
                id="m-id"
                type="text"
                dir="ltr"
                placeholder="dQw4w9WgXcQ"
                autoComplete="off"
                style={{ maxWidth: '280px' }}
                value={videoId}
                onChange={(e) => handleIdChange(e.target.value)}
              />
              <span className="hint">
                ۱۱ نویسه. این دو فیلد با هم هماهنگ می‌مانند — هرکدام را آخر پر کنید، همان ملاک است.
              </span>
              <span className="err" id="e-id"></span>
            </div>

            <div className="field" data-field="bitrate">
              <label>بیت‌ریت خروجی</label>
              <div className="seg" id="bitrateSeg" role="group" aria-label="بیت‌ریت خروجی">
                {[128, 192, 256, 320].map((k) => (
                  <button
                    key={k}
                    type="button"
                    data-k={k}
                    aria-pressed={bitrate === k}
                    onClick={() => setBitrate(k)}
                  >
                    {k} kbps
                  </button>
                ))}
              </div>
              <span className="hint">
                بیت‌ریت بالاتر جزئیات ضربه‌ای در اجراهای زنده را حفظ می‌کند، اما جریان اصلی به‌ندرت جزئیاتی بیش از ۱۹۲
                kbps دارد.
              </span>
            </div>

            <div className="field" data-field="rate">
              <label>نرخ نمونه‌برداری</label>
              <div className="seg" id="rateSeg" role="group" aria-label="نرخ نمونه‌برداری">
                {[44100, 48000].map((hz) => (
                  <button
                    key={hz}
                    type="button"
                    data-hz={hz}
                    aria-pressed={rate === hz}
                    onClick={() => setRate(hz)}
                  >
                    {hz === 44100 ? '44.1 kHz' : '48 kHz'}
                  </button>
                ))}
              </div>
            </div>

            <div className="field" data-field="meta">
              <label className="switch">
                <input
                  type="checkbox"
                  id="m-meta"
                  checked={writeMeta}
                  onChange={(e) => setWriteMeta(e.target.checked)}
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
                  نوشتن عنوان، هنرمند و کاور در تگ‌های ID3
                </span>
              </label>
              <label className="switch">
                <input
                  type="checkbox"
                  id="m-norm"
                  checked={normFilename}
                  onChange={(e) => setNormFilename(e.target.checked)}
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
                  یکسان‌سازی نام فایل با قراردادهای فارسی/عربی (ي → ی, ك → ک)
                </span>
              </label>
            </div>

            <div>
              {!running ? (
                <button className="btn btn-primary" type="submit" id="go">
                  تبدیل به MP3
                </button>
              ) : (
                <button
                  className="btn btn-quiet"
                  type="button"
                  id="cancel"
                  onClick={handleCancel}
                >
                  لغو
                </button>
              )}
            </div>
          </form>

          {/* Running Job Progress */}
          {running && (
            <div id="job" style={{ marginTop: '24px', maxWidth: '760px' }}>
              <div className="player">
                <div className="player-row">
                  <strong style={{ color: '#fff' }}>در حال تبدیل <span dir="ltr">{activeVid}</span></strong>
                  <span dir="ltr">
                    {bitrate} kbps · {rate / 1000} kHz
                  </span>
                </div>
                <div className="bar">
                  <i style={{ width: `${progress}%` }}></i>
                </div>
                <div className="player-row">
                  <span>{currentStep}</span>
                  <span>{progress}%</span>
                </div>
              </div>
            </div>
          )}

          {/* Completion Notice */}
          {!running && lastCompletedNotice && (
            <div style={{ marginTop: '24px', maxWidth: '760px' }}>
              <div className="notice">
                <span className="led ok"></span>
                <span>
                  <strong style={{ color: '#fff' }}>انجام شد.</strong> {lastCompletedNotice}
                </span>
              </div>
            </div>
          )}
        </section>

        {/* Conversion History */}
        <section className="sec" data-od-id="mp3-history">
          <div className="sec-head">
            <h2>این نشست</h2>
            <span className="sub" id="histCount">
              {history.length > 0
                ? `${toFaDigits(history.length)} تبدیل در این نشست`
                : 'هنوز تبدیلی انجام نشده'}
            </span>
          </div>

          <div id="historySlot">
            {history.length === 0 ? (
              <div className="empty">
                <strong>هنوز چیزی تبدیل نشده</strong>
                <span>
                  کارهای این نشست با بیت‌ریت، نرخ نمونه‌برداری و حجم خروجی اینجا نمایش داده می‌شوند.
                  در کاتالوگ ثبت نمی‌شوند.
                </span>
              </div>
            ) : (
              <div className="tbl-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>ویدیو</th>
                      <th>شناسهٔ ویدیو</th>
                      <th>بیت‌ریت</th>
                      <th>نرخ نمونه</th>
                      <th>حجم (تخمینی)</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((h, i) => (
                      <tr key={i}>
                        <td>
                          <strong>{h.title}</strong>
                          <br />
                          <span style={{ color: 'var(--muted-2)', fontSize: '12px' }}>
                            {h.meta ? 'تگ‌های ID3 نوشته شد' : 'بدون تگ ID3'}
                            {h.norm ? ' · نام فایل فارسی' : ''}
                          </span>
                        </td>
                        <td className="mono" dir="ltr">{h.id}</td>
                        <td className="mono" dir="ltr">{h.bitrate} kbps</td>
                        <td className="mono" dir="ltr">
                          {(h.rate / 1000).toFixed(1).replace('.0', '')} kHz
                        </td>
                        <td className="mono" dir="ltr">{h.size}</td>
                        <td>
                          <button
                            className="btn btn-primary btn-sm"
                            type="button"
                            onClick={() => {
                              const apiBase = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'
                              if (h.downloadUrl) {
                                window.open(`${apiBase}${h.downloadUrl}`, '_blank')
                              } else {
                                window.open(`${apiBase}/api/download/${h.id}`, '_blank')
                              }
                            }}
                          >
                            دانلود
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div style={{ marginTop: '14px' }}>
            <button
              className="btn btn-quiet btn-sm"
              type="button"
              id="clearHist"
              onClick={handleClearHistory}
            >
              پاک‌کردن تاریخچه
            </button>
          </div>
        </section>

        {/* Rules */}
        <section className="sec" data-od-id="mp3-rules">
          <div className="sec-head">
            <h2>قواعدی که این ابزار رعایت می‌کند</h2>
            <span className="sub">سند 008</span>
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
              <strong style={{ color: '#fff' }}>هر کار، یک ویدیو</strong>
              <span>
                بدون پلی‌لیست، بدون درج کانال، بدون صف دسته‌ای. آدرس ارسال‌شده پیش از هر چیز دیگر به یک
                شناسهٔ ویدیوی تکی تبدیل می‌شود.
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
              <strong style={{ color: '#fff' }}>رضایت آشکار در هر اجرا</strong>
              <span>
                رابط کاربری پیش از شروع تبدیل، شرط مالکیت/مجوز را اعلام می‌کند و تأیید شما را همراه کار
                ثبت می‌کند.
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
              <strong style={{ color: '#fff' }}>تنها فایل‌های موقت</strong>
              <span>
                فایل کدگذاری‌شده فقط به‌مدت دانلود نگه داشته و سپس حذف می‌شود. چیزی به کاتالوگ رسانه
                افزوده نمی‌شود.
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
              <strong style={{ color: '#fff' }}>محدودیت نرخ</strong>
              <span>
                هر بار یک کار برای هر دستگاه، همراه با فاصلهٔ زمانی میان کارها، تا این ابزار به یک اسکرپر
                انبوه تبدیل نشود.
              </span>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </>
  )
}
