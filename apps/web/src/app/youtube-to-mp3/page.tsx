'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Header } from '@/components/Header'
import { Footer } from '@/components/Footer'
import { useToast } from '@/components/ui/ToastNotification'
import { fmtMiB } from '@/lib/catalog'

interface JobHistory {
  id: string
  title: string
  bitrate: number
  rate: number
  size: string
  meta: boolean
  norm: boolean
}

const STEPS = [
  'Resolving video ID',
  'Reading available audio streams',
  'Extracting audio track',
  'Encoding MP3',
  'Finalising tags',
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
    showToast('Job cancelled — the partial file was discarded')
  }

  // Finish job
  function finishJob(vid: string) {
    if (timerRef.current) clearInterval(timerRef.current)
    setRunning(false)
    setProgress(100)

    const secs = 240
    const bytes = calcMp3Bytes(secs, bitrate)
    const title = `youtube-${vid}`
    const sizeStr = fmtMiB(bytes)

    const newJob: JobHistory = {
      id: vid,
      title,
      bitrate,
      rate,
      size: sizeStr,
      meta: writeMeta,
      norm: normFilename,
    }

    setHistory((prev) => [newJob, ...prev])
    setLastCompletedNotice(
      `Encoded ${bitrate} kbps / ${rate / 1000} kHz — ${sizeStr} for the 4-minute reference runtime (estimated; this prototype never contacts YouTube). The file lives in this session only and is never added to the catalogue.`
    )
    showToast(`Conversion finished — ${sizeStr}`)
  }

  // Form submit
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (running) {
      showToast('One job at a time — cancel the running job first', 'error')
      return
    }

    const raw = url.trim() || videoId.trim()
    if (!raw) {
      setErrors({ url: 'Paste a YouTube URL or an 11-character video ID.' })
      return
    }

    const vid = extractVideoId(raw) || (ID_RE.test(raw) ? raw : '')
    if (!vid) {
      setErrors({
        url: 'No 11-character video ID found in that address. Playlists and channel links are rejected.',
      })
      return
    }

    if (!ID_RE.test(vid)) {
      setErrors({ url: 'That video ID is not 11 characters.' })
      return
    }

    const now = Date.now()
    const since = now - lastRunRef.current
    if (since < 4000) {
      showToast(
        `Rate limited — wait ${Math.ceil((4000 - since) / 1000)}s before the next job`,
        'error'
      )
      return
    }

    setErrors({})
    setRunning(true)
    lastRunRef.current = now
    setActiveVid(vid)
    setProgress(0)
    setCurrentStep('Starting…')
    setLastCompletedNotice(null)

    let step = 0
    timerRef.current = setInterval(() => {
      step++
      const pct = Math.min(100, Math.round((step / STEPS.length) * 100))
      setProgress(pct)
      setCurrentStep(STEPS[Math.min(step, STEPS.length - 1)])

      if (pct >= 100) {
        finishJob(vid)
      }
    }, 520)
  }

  function handleClearHistory() {
    if (history.length === 0) {
      showToast('History is already empty')
      return
    }
    setHistory([])
    showToast('Session history cleared')
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
            <span className="pill-red">Declared exception</span>
            <span className="pill-ghost">
              Spec 008 · FR relaxes Constitution Principle III for this tool only
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
            YouTube to MP3
          </h1>
          <p className="hero-desc" style={{ marginTop: '14px' }}>
            Everywhere else in this product the server links out and relays nothing. This tool is
            the one declared exception: it fetches the audio stream, encodes it and hands you a
            file. One video at a time, no playlists, no batch queue.
          </p>
          <div className="notice warn" style={{ marginTop: '20px' }}>
            <span className="led warn"></span>
            <span>
              Only convert material you own or are licensed to download. This prototype runs the
              full interface — validation, bitrate tiers, progress, history — without contacting
              YouTube.
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
              <label htmlFor="m-url">YouTube video URL</label>
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
              <label htmlFor="m-id">…or paste just the video ID</label>
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
                11 characters. The two fields stay in sync — whichever you fill last wins.
              </span>
              <span className="err" id="e-id"></span>
            </div>

            <div className="field" data-field="bitrate">
              <label>Output bitrate</label>
              <div className="seg" id="bitrateSeg" role="group" aria-label="Output bitrate">
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
                Higher bitrate keeps transients in live sets but the source stream rarely carries
                more detail than 192 kbps.
              </span>
            </div>

            <div className="field" data-field="rate">
              <label>Sample rate</label>
              <div className="seg" id="rateSeg" role="group" aria-label="Sample rate">
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
                  Write title, artist and cover art into the ID3 tags
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
                  Normalise the filename to Persian/Arabic conventions (ي → ی, ك → ک)
                </span>
              </label>
            </div>

            <div>
              {!running ? (
                <button className="btn btn-primary" type="submit" id="go">
                  Convert to MP3
                </button>
              ) : (
                <button
                  className="btn btn-quiet"
                  type="button"
                  id="cancel"
                  onClick={handleCancel}
                >
                  Cancel
                </button>
              )}
            </div>
          </form>

          {/* Running Job Progress */}
          {running && (
            <div id="job" style={{ marginTop: '24px', maxWidth: '760px' }}>
              <div className="player">
                <div className="player-row">
                  <strong style={{ color: '#fff' }}>Converting {activeVid}</strong>
                  <span>
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
                  <strong style={{ color: '#fff' }}>Done.</strong> {lastCompletedNotice}
                </span>
              </div>
            </div>
          )}
        </section>

        {/* Conversion History */}
        <section className="sec" data-od-id="mp3-history">
          <div className="sec-head">
            <h2>This session</h2>
            <span className="sub" id="histCount">
              {history.length > 0
                ? `${history.length} conversion${history.length > 1 ? 's' : ''} this session`
                : 'no conversions yet'}
            </span>
          </div>

          <div id="historySlot">
            {history.length === 0 ? (
              <div className="empty">
                <strong>Nothing converted yet</strong>
                <span>
                  Jobs from this session appear here with their bitrate, sample rate and output
                  size. They are not written to the catalogue.
                </span>
              </div>
            ) : (
              <div className="tbl-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Video</th>
                      <th>Video ID</th>
                      <th>Bitrate</th>
                      <th>Sample</th>
                      <th>Size (est.)</th>
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
                            {h.meta ? 'ID3 tags written' : 'no ID3 tags'}
                            {h.norm ? ' · Persian filename' : ''}
                          </span>
                        </td>
                        <td className="mono">{h.id}</td>
                        <td className="mono">{h.bitrate} kbps</td>
                        <td className="mono">
                          {(h.rate / 1000).toFixed(1).replace('.0', '')} kHz
                        </td>
                        <td className="mono">{h.size}</td>
                        <td>
                          <button
                            className="btn btn-primary btn-sm"
                            type="button"
                            onClick={() =>
                              showToast(
                                'Prototype: the encoded file would be served from this route — nothing was fetched'
                              )
                            }
                          >
                            Download
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
              Clear history
            </button>
          </div>
        </section>

        {/* Rules */}
        <section className="sec" data-od-id="mp3-rules">
          <div className="sec-head">
            <h2>Rules this tool follows</h2>
            <span className="sub">spec 008</span>
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
              <strong style={{ color: '#fff' }}>One video per job</strong>
              <span>
                No playlists, no channel dumps, no batch queue. A submitted URL is reduced to a
                single video ID before anything else happens.
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
              <strong style={{ color: '#fff' }}>Explicit consent per run</strong>
              <span>
                The interface states the ownership/licence requirement before conversion starts,
                and records the acknowledgement with the job.
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
              <strong style={{ color: '#fff' }}>Transient files only</strong>
              <span>
                The encoded file is held for the duration of the download and then discarded.
                Nothing is added to the media catalogue.
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
              <strong style={{ color: '#fff' }}>Rate limited</strong>
              <span>
                One job at a time per device, with a cooldown between jobs, so the tool cannot be
                turned into a bulk scraper.
              </span>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </>
  )
}
