'use client'

import React, { useEffect } from 'react'
import type { CatalogItem, CatalogMovie, CatalogGame, CatalogMusic } from '@/lib/catalog'
import { toFaDigits, fmtMiB } from '@/lib/catalog'
import { copyToClipboard } from '@/lib/clipboard'
import { useToast } from '@/components/ui/ToastNotification'
import { X, Play, AlertTriangle, Lock, Download, Copy, Check } from 'lucide-react'

interface DetailDrawerProps {
  item: CatalogItem | null
  isOpen: boolean
  onClose: () => void
  onPlayStream?: (url: string, title: string) => void
}

export function DetailDrawer({ item, isOpen, onClose, onPlayStream }: DetailDrawerProps) {
  const { showToast } = useToast()
  const [copiedText, setCopiedText] = React.useState<string | null>(null)

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    if (isOpen) {
      document.body.style.overflow = 'hidden'
      window.addEventListener('keydown', handleKeyDown)
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onClose])

  if (!isOpen || !item) return null

  async function handleCopy(text: string, label: string) {
    const ok = await copyToClipboard(text)
    if (ok) {
      setCopiedText(text)
      showToast(`${label} کپی شد`, 'success')
      setTimeout(() => setCopiedText(null), 2000)
    } else {
      showToast('خطا در کپی', 'error')
    }
  }

  function handleDownloadClick(e: React.MouseEvent, title: string) {
    e.preventDefault()
    showToast(`شروع دانلود برای «${title}»`, 'success')
  }

  // Header image logic
  const artSrc =
    item.cat === 'music'
      ? item.art
      : item.cat === 'games'
        ? `/images/keys/${item.id}.jpg`
        : `/images/backdrops/${item.id}.jpg`

  return (
    <>
      <div className={`scrim ${isOpen ? 'on' : ''}`} onClick={onClose} />
      <aside
        className={`drawer ${isOpen ? 'on' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label="Release details"
      >
        <div className="drawer-top">
          <button
            className="drawer-close"
            type="button"
            aria-label="Close details"
            onClick={onClose}
          >
            <X className="w-5 h-5 text-white" />
          </button>
          <img
            src={artSrc}
            alt={`${item.title} artwork`}
            onError={(e) => {
              // Fallback to poster art if backdrop doesn't exist
              ;(e.target as HTMLImageElement).src = item.art
            }}
          />
        </div>

        <div className="drawer-body" tabIndex={-1}>
          {/* Drawer Header Block */}
          <div className="drawer-head">
            <div className="eyebrow">
              <span className="pill-red">
                {item.cat === 'games'
                  ? (item as CatalogGame).releaseGroup
                  : item.cat === 'music'
                    ? 'Album'
                    : (item as CatalogMovie).kind === 'tv'
                      ? 'Series'
                      : 'Feature'}
              </span>
              <span className="pill-ghost">
                {item.cat === 'movies'
                  ? 'Movie'
                  : item.cat === 'games'
                    ? 'Game'
                    : 'Track'}
              </span>
              {'censored' in item && item.censored && (
                <span className="pill-ghost">Censored cut</span>
              )}
              {item.rating != null && (
                <span className="pill-ghost">IMDb {item.rating.toFixed(1)}/10</span>
              )}
            </div>

            <h2>{item.title}</h2>

            {item.fa && (
              <p className="hero-meta" lang="fa" dir="rtl">
                <strong style={{ fontSize: '20px' }}>{item.fa}</strong>
              </p>
            )}
          </div>

          <p className="hero-desc">{item.blurb}</p>

          {/* MOVIE BODY */}
          {item.cat === 'movies' && (
            <>
              <div className="drawer-sec">
                <h3>Formats available</h3>
                <table className="vtable">
                  <thead>
                    <tr>
                      <th>Quality</th>
                      <th>Codec</th>
                      <th>Audio</th>
                      <th>Size</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {(item as CatalogMovie).variants.map((v, idx) => (
                      <tr key={idx}>
                        <td className="res">{v.res}</td>
                        <td>{v.codec}</td>
                        <td>{v.audio}</td>
                        <td className="num">
                          {fmtMiB(v.bytes)}{' '}
                          <span style={{ color: 'var(--muted-2)' }}>(est.)</span>
                        </td>
                        <td>
                          <a
                            className="btn btn-primary btn-sm"
                            href="#"
                            onClick={(e) =>
                              handleDownloadClick(
                                e,
                                `${item.title} · ${v.res} · ${v.codec}`
                              )
                            }
                          >
                            <Download className="w-3.5 h-3.5" />
                            <span>Download</span>
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {(item as CatalogMovie).stream ? (
                  <div className="notice" style={{ marginTop: '14px' }}>
                    <Play className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>
                      Upstream serves this title as a directly playable stream, so an in-browser player
                      is offered next to the download links. Nothing is proxied.
                    </span>
                    {onPlayStream && (
                      <button
                        type="button"
                        onClick={() =>
                          onPlayStream(
                            'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
                            item.title
                          )
                        }
                        className="btn btn-primary btn-sm"
                        style={{ marginInlineStart: 'auto' }}
                      >
                        Play in browser
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="notice warn" style={{ marginTop: '14px' }}>
                    <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                    <span>
                      Upstream blocks hotlinking or requires a player token, so no player is shown here.
                      Clean direct download links only — no error screen, no pop-ups.
                    </span>
                  </div>
                )}
              </div>

              <div className="drawer-sec">
                <h3>Details</h3>
                <dl className="kv">
                  <dt>Year</dt>
                  <dd>{toFaDigits(item.year)}</dd>
                  <dt>Genre</dt>
                  <dd>{item.genres}</dd>
                  <dt>Original audio</dt>
                  <dd>{item.audio}</dd>
                  {'censored' in item && item.censored && (
                    <>
                      <dt>Cut</dt>
                      <dd>Censored release — uncensored variants are filtered by Tier 2+ setting</dd>
                    </>
                  )}
                  <dt>Delivery</dt>
                  <dd>
                    Direct link to the upstream CDN. This site stores, proxies and relays nothing
                    (Constitution Principle III).
                  </dd>
                </dl>
              </div>

              <div className="drawer-sec">
                <h3>Resolved from 4 sources</h3>
                <div className="prov">
                  <span className="led ok"></span>
                  <strong style={{ color: '#e8e8e8' }}>Film2Media</strong>
                  <span>Tier 1</span>
                  <span style={{ color: 'var(--muted-2)' }}>poster, dub + soft-sub variants, 4K</span>
                </div>
                <div className="prov">
                  <span className="led ok"></span>
                  <strong style={{ color: '#e8e8e8' }}>AvaMovie</strong>
                  <span>Tier 1</span>
                  <span style={{ color: 'var(--muted-2)' }}>largest movie mirror set</span>
                </div>
              </div>
            </>
          )}

          {/* GAME BODY */}
          {item.cat === 'games' && (
            <>
              <div className="drawer-sec">
                <h3>Archive</h3>
                <dl className="kv">
                  <dt>Release group</dt>
                  <dd>{(item as CatalogGame).releaseGroup}</dd>
                  <dt>Version</dt>
                  <dd>{(item as CatalogGame).version}</dd>
                  <dt>Parts</dt>
                  <dd>
                    {toFaDigits((item as CatalogGame).parts.length)} parts
                  </dd>
                  <dt>Total size</dt>
                  <dd>
                    {fmtMiB((item as CatalogGame).totalBytes)}{' '}
                    <span style={{ color: 'var(--muted-2)' }}>(est.)</span>
                  </dd>
                </dl>
              </div>

              <div className="drawer-sec">
                <h3>Extraction</h3>
                {(item as CatalogGame).password ? (
                  <div className="pw">
                    <span
                      style={{
                        fontSize: '12px',
                        letterSpacing: '.1em',
                        textTransform: 'uppercase',
                        color: 'var(--muted)',
                      }}
                    >
                      Extraction password
                    </span>
                    <code>{(item as CatalogGame).password}</code>
                    <button
                      className="btn btn-ghost btn-sm"
                      type="button"
                      onClick={() =>
                        handleCopy(
                          (item as CatalogGame).password || '',
                          'رمز فایل'
                        )
                      }
                    >
                      {copiedText === (item as CatalogGame).password ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                      <span>Copy password</span>
                    </button>
                  </div>
                ) : (
                  <div className="notice">
                    <Lock className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>This release has no archive password.</span>
                  </div>
                )}
              </div>

              <div className="drawer-sec">
                <h3>Parts in order</h3>
                <table className="vtable">
                  <thead>
                    <tr>
                      <th>Segment</th>
                      <th>Size</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {(item as CatalogGame).parts.map((p) => (
                      <tr key={p.n}>
                        <td className="num" style={{ width: '64px' }}>
                          Part {toFaDigits(p.n)}
                        </td>
                        <td className="num">
                          {fmtMiB(p.bytes)}{' '}
                          <span style={{ color: 'var(--muted-2)' }}>(est.)</span>
                        </td>
                        <td style={{ textAlign: 'end' }}>
                          <a
                            className="btn btn-ghost btn-sm"
                            href="#"
                            onClick={(e) => handleDownloadClick(e, `Part ${p.n}`)}
                          >
                            Get part
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <div className="hero-cta" style={{ marginTop: '14px' }}>
                  <button
                    className="btn btn-primary"
                    type="button"
                    onClick={() => {
                      const batch = (item as CatalogGame).parts
                        .map(
                          (p) =>
                            `https://upstream.example/${item.id}/part${p.n}.rar`
                        )
                        .join('\n')
                      handleCopy(batch, 'لینک تمام پارت‌ها')
                    }}
                  >
                    Copy all links
                  </button>
                </div>
                <p
                  className="hint"
                  style={{
                    marginTop: '10px',
                    color: 'var(--muted-2)',
                    fontSize: '12px',
                  }}
                >
                  Copied lines are one URL per line, ordered Part 1 → Part N — paste straight into
                  Free Download Manager, JDownloader or wget.
                </p>
              </div>

              <div className="drawer-sec">
                <h3>Resolved from 4 sources</h3>
                <div className="prov">
                  <span className="led ok"></span>
                  <strong style={{ color: '#e8e8e8' }}>YasDL</strong>
                  <span>Tier 1</span>
                  <span style={{ color: 'var(--muted-2)' }}>ordered parts + password on page</span>
                </div>
                <div className="prov">
                  <span className="led ok"></span>
                  <strong style={{ color: '#e8e8e8' }}>Downloadha</strong>
                  <span>Tier 2</span>
                  <span style={{ color: 'var(--muted-2)' }}>fallback mirror</span>
                </div>
              </div>
            </>
          )}

          {/* MUSIC BODY */}
          {item.cat === 'music' && (
            <>
              <div className="drawer-sec">
                <h3>Preview</h3>
                <div className="player">
                  <div className="player-row">
                    <img
                      src={item.art}
                      alt=""
                      width="56"
                      height="56"
                      style={{
                        width: '56px',
                        height: '56px',
                        borderRadius: '6px',
                        objectFit: 'cover',
                      }}
                    />
                    <div>
                      <strong style={{ color: '#fff', fontSize: '15px' }}>
                        {item.title}
                      </strong>
                      <div>
                        {(item as CatalogMusic).artist} ·{' '}
                        <span lang="fa" dir="rtl">
                          {(item as CatalogMusic).artistFa}
                        </span>{' '}
                        · {toFaDigits(item.year)}
                      </div>
                    </div>
                  </div>
                  <audio
                    controls
                    preload="none"
                    src={`/audio/${item.id}-preview.mp3`}
                    style={{ width: '100%', marginTop: '10px' }}
                  />
                  <div className="player-row" style={{ fontSize: '12px', color: 'var(--muted-2)' }}>
                    MusicBrainz release {(item as CatalogMusic).mbid} · sizes computed from the
                    real track duration, not stored.
                  </div>
                </div>
              </div>

              <div className="drawer-sec">
                <h3>Tracks</h3>
                <table className="vtable">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Title</th>
                      <th>128k</th>
                      <th>320k</th>
                      <th>Get</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(item as CatalogMusic).tracks.map((t) => (
                      <tr key={t.n}>
                        <td className="num" style={{ width: '40px' }}>
                          {toFaDigits(t.n)}
                        </td>
                        <td>
                          <strong>{t.title}</strong>
                          <br />
                          <span className="num">
                            {Math.floor(t.sec / 60)}:
                            {String(t.sec % 60).padStart(2, '0')}
                          </span>
                        </td>
                        <td className="num">{fmtMiB(t.lo)}</td>
                        <td className="num">{fmtMiB(t.hi)}</td>
                        <td style={{ whiteSpace: 'nowrap' }}>
                          <a
                            className="btn btn-ghost btn-sm"
                            href="#"
                            style={{ marginInlineEnd: '6px' }}
                            onClick={(e) => handleDownloadClick(e, `${t.title} 128k`)}
                          >
                            128k
                          </a>
                          <a
                            className="btn btn-primary btn-sm"
                            href="#"
                            onClick={(e) => handleDownloadClick(e, `${t.title} 320k`)}
                          >
                            320k
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="drawer-sec">
                <h3>Resolved from 4 sources</h3>
                <div className="prov">
                  <span className="led ok"></span>
                  <strong style={{ color: '#e8e8e8' }}>Nex1Music</strong>
                  <span>Tier 1</span>
                  <span style={{ color: 'var(--muted-2)' }}>128/320 tiers per track</span>
                </div>
                <div className="prov">
                  <span className="led ok"></span>
                  <strong style={{ color: '#e8e8e8' }}>Pop-Music</strong>
                  <span>Tier 2</span>
                  <span style={{ color: 'var(--muted-2)' }}>album-oriented</span>
                </div>
              </div>
            </>
          )}
        </div>
      </aside>
    </>
  )
}
