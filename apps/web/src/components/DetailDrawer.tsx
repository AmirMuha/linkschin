'use client'

import React, { useEffect } from 'react'
import type { CatalogItem, CatalogMovie, CatalogGame, CatalogMusic } from '@/lib/catalog'
import type { MediaItem } from '@/types/media'
import { toFaDigits, fmtMiB, getCatalogItemById } from '@/lib/catalog'
import { copyToClipboard } from '@/lib/clipboard'
import { useToast } from '@/components/ui/ToastNotification'
import { TechnicalText } from '@/components/ui/TechnicalText'
import { X, Play, AlertTriangle, Lock, Download, Copy, Check, Heart, Undo2, ExternalLink } from 'lucide-react'
import { GamePartList } from '@/components/cards/GamePartList'
import { MovieDownloadMatrix } from '@/components/cards/MovieDownloadMatrix'

export type DrawerItem = CatalogItem | MediaItem

function isMediaItem(item: DrawerItem): item is MediaItem {
  return 'category' in item
}

interface DetailDrawerProps {
  item: DrawerItem | null
  isOpen: boolean
  onClose: () => void
  onPlayStream?: (url: string, title: string) => void
  onToggleFavorite?: (item: any) => void
  isItemFavorite?: (id: string) => boolean
  /** Set when the last write to storage was rejected — likes are session-only. */
  persistenceBlocked?: boolean
}

export function DetailDrawer({
  item,
  isOpen,
  onClose,
  onPlayStream,
  onToggleFavorite,
  isItemFavorite,
  persistenceBlocked,
}: DetailDrawerProps) {
  const { showToast } = useToast()
  const [copiedText, setCopiedText] = React.useState<string | null>(null)
  // The last like/unlike, kept only long enough for the drawer to offer Undo.
  const [lastAction, setLastAction] = React.useState<{
    id: string
    added: boolean
  } | null>(null)

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

  function handleToggleFavorite() {
    if (!item || !onToggleFavorite) return
    const wasLiked = isItemFavorite?.(item.id) ?? false
    onToggleFavorite(item)
    setLastAction({ id: item.id, added: !wasLiked })
    showToast(
      wasLiked ? 'از علاقه‌مندی‌ها حذف شد' : 'به علاقه‌مندی‌ها افزوده شد',
      'success'
    )
  }

  function handleUndo() {
    if (!lastAction || !onToggleFavorite) return
    const target = getCatalogItemById(lastAction.id)
    if (target) onToggleFavorite(target)
    else if (item && item.id === lastAction.id) onToggleFavorite(item as any)
    setLastAction(null)
  }

  const isMedia = isMediaItem(item)
  const category = isMedia ? item.category : item.cat

  // Header image logic
  const artSrc = isMedia
    ? (item.poster_url || (category === 'games' ? `/images/keys/${item.id}.jpg` : `/images/backdrops/${item.id}.jpg`))
    : item.cat === 'music'
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
        aria-label="جزئیات انتشار"
      >
        <div className="drawer-top">
          <button
            className="drawer-close"
            type="button"
            aria-label="بستن جزئیات"
            onClick={onClose}
          >
            <X className="w-5 h-5 text-white" />
          </button>
          <img
            src={artSrc}
            alt={`${item.title} artwork`}
            onError={(e) => {
              // Fallback to poster art if backdrop doesn't exist
              if (!isMedia) {
                ;(e.target as HTMLImageElement).src = item.art
              } else if (item.poster_url && artSrc !== item.poster_url) {
                ;(e.target as HTMLImageElement).src = item.poster_url
              }
            }}
          />
        </div>

        <div className="drawer-body" tabIndex={-1}>
          {/* Drawer Header Block */}
          <div className="drawer-head">
            <div className="eyebrow">
              <span className="pill-red">
                {category === 'games'
                  ? (isMedia
                      ? item.game_releases?.[0]?.release_group || 'بازی'
                      : (item as CatalogGame).releaseGroup)
                  : category === 'music'
                    ? 'آلبوم'
                    : isMedia
                      ? 'فیلم'
                      : (item as CatalogMovie).kind === 'tv'
                        ? 'سریال'
                        : 'فیلم سینمایی'}
              </span>
              <span className="pill-ghost">
                {category === 'movies'
                  ? 'فیلم'
                  : category === 'games'
                    ? 'بازی'
                    : 'آهنگ'}
              </span>
              {isMedia ? (
                item.censorship_status === 'censored' && (
                  <span className="pill-ghost">نسخه بازبینی‌شده</span>
                )
              ) : (
                'censored' in item && item.censored && (
                  <span className="pill-ghost">نسخه بازبینی‌شده</span>
                )
              )}
              {isMedia ? (
                item.imdb_rating != null && (
                  <span className="pill-ghost">IMDb {item.imdb_rating.toFixed(1)}/10</span>
                )
              ) : (
                item.rating != null && (
                  <span className="pill-ghost">IMDb {item.rating.toFixed(1)}/10</span>
                )
              )}
            </div>

            <h2>{item.title}</h2>

            {(isMedia ? item.original_title : item.fa) && (
              <p className="hero-meta" lang="fa" dir="rtl">
                <strong style={{ fontSize: '20px' }}>
                  {isMedia ? item.original_title : item.fa}
                </strong>
              </p>
            )}
          </div>

          <p className="hero-desc">{isMedia ? item.description : item.blurb}</p>

          {/* MOVIE BODY */}
          {category === 'movies' && (
            isMedia ? (
              <div className="drawer-sec">
                <h3>کیفیت‌ها و لینک‌های دانلود</h3>
                {item.movie_variants && item.movie_variants.length > 0 ? (
                  <MovieDownloadMatrix variants={item.movie_variants} />
                ) : item.watch_url ? (
                  <a
                    href={item.watch_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-primary btn-sm inline-flex items-center gap-2"
                  >
                    <span>مشاهده در سایت منبع</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                ) : (
                  <p className="text-sm text-zinc-400">لینکی یافت نشد.</p>
                )}
              </div>
            ) : (
              <>
                <div className="drawer-sec">
                <h3>فرمت‌های موجود</h3>
                <table className="vtable">
                  <thead>
                    <tr>
                      <th>کیفیت</th>
                      <th>کدک</th>
                      <th>صدا</th>
                      <th>حجم</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {(item as CatalogMovie).variants.map((v, idx) => (
                      <tr key={idx}>
                        <td className="res">
                          <TechnicalText>{v.res}</TechnicalText>
                        </td>
                        <td>
                          <TechnicalText>{v.codec}</TechnicalText>
                        </td>
                        <td>
                          <TechnicalText>{v.audio}</TechnicalText>
                        </td>
                        <td className="num">
                          <TechnicalText>{fmtMiB(v.bytes)}</TechnicalText>{' '}
                          <span style={{ color: 'var(--muted-2)' }}>(تخمینی)</span>
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
                            <span>دانلود</span>
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
                      سایت منبع این عنوان را به‌صورت پخش‌کننده مستقیم ارائه می‌کند، بنابراین پخش‌کننده
                      مرورگر در کنار لینک‌های دانلود نمایش داده می‌شود. هیچ فایلی از این سایت پروکسی نمی‌شود.
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
                        پخش در مرورگر
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="notice warn" style={{ marginTop: '14px' }}>
                    <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                    <span>
                      سایت منبع لینک‌دهی مستقیم را مسدود کرده یا توکن پخش‌کننده می‌خواهد، بنابراین
                      پخش‌کننده‌ای نمایش داده نمی‌شود. تنها لینک‌های دانلود مستقیم و تمیز — بدون صفحه
                      خطا و بدون پنجره تبلیغاتی.
                    </span>
                  </div>
                )}
              </div>

              <div className="drawer-sec">
                <h3>جزئیات</h3>
                <dl className="kv">
                  <dt>سال انتشار</dt>
                  <dd>{toFaDigits((item as CatalogMovie).year)}</dd>
                  <dt>ژانر</dt>
                  <dd>{(item as CatalogMovie).genres}</dd>
                  <dt>صدای اصلی</dt>
                  <dd>
                    <TechnicalText>{(item as CatalogMovie).audio}</TechnicalText>
                  </dd>
                  {'censored' in item && item.censored && (
                    <>
                      <dt>نسخه</dt>
                      <dd>
                        انتشار بازبینی‌شده — نسخه‌های بازبینی‌نشده بر اساس تنظیم سطح ۲ به بالا فیلتر
                        می‌شوند
                      </dd>
                    </>
                  )}
                  <dt>روش تحویل</dt>
                  <dd>
                    لینک مستقیم به CDN سایت منبع. این سایت هیچ فایلی را ذخیره، پروکسی یا بازارسال
                    نمی‌کند (بند ۳ منشور).
                  </dd>
                </dl>
              </div>

              <div className="drawer-sec">
                <h3>منابع پشتیبان</h3>
                <div className="prov">
                  <span className="led ok"></span>
                  <strong style={{ color: '#e8e8e8' }}>Film2Media</strong>
                  <span>سطح ۱</span>
                  <span style={{ color: 'var(--muted-2)' }}>
                    پوستر، نسخه دوبله و زیرنویس نرم، 4K
                  </span>
                </div>
                <div className="prov">
                  <span className="led ok"></span>
                  <strong style={{ color: '#e8e8e8' }}>AvaMovie</strong>
                  <span>سطح ۱</span>
                  <span style={{ color: 'var(--muted-2)' }}>
                    بزرگ‌ترین مجموعه آینه فیلم
                  </span>
                </div>
              </div>
            </>
          )
        )}

          {/* GAME BODY */}
          {category === 'games' && (
            isMedia ? (
              <>
                {item.game_releases && item.game_releases.length > 0 ? (
                  item.game_releases.map((release, relIdx) => (
                    <React.Fragment key={release.id || relIdx}>
                      <div className="drawer-sec">
                        <h3>
                          {item.game_releases.length > 1
                            ? `آرشیو ${toFaDigits(relIdx + 1)} · مشخصات`
                            : 'مشخصات انتشار'}
                        </h3>
                        <dl className="kv">
                          {release.release_group && (
                            <>
                              <dt>گروه انتشار</dt>
                              <dd>
                                <TechnicalText>{release.release_group}</TechnicalText>
                              </dd>
                            </>
                          )}
                          {release.version && (
                            <>
                              <dt>نسخه</dt>
                              <dd>
                                <TechnicalText>{release.version}</TechnicalText>
                              </dd>
                            </>
                          )}
                          <dt>تعداد پارت</dt>
                          <dd>{toFaDigits(release.parts.length)} پارت</dd>
                          {release.total_size && (
                            <>
                              <dt>حجم کل</dt>
                              <dd>
                                <TechnicalText>{release.total_size}</TechnicalText>
                              </dd>
                            </>
                          )}
                          <dt>منبع</dt>
                          <dd>{item.source_id}</dd>
                        </dl>
                      </div>

                      {release.archive_password && (
                        <div className="drawer-sec">
                          <h3>استخراج</h3>
                          <div className="pw">
                            <span
                              style={{
                                fontSize: '12px',
                                letterSpacing: '.1em',
                                textTransform: 'uppercase',
                                color: 'var(--muted)',
                              }}
                            >
                              رمز استخراج آرشیو
                            </span>
                            <TechnicalText as="code">
                              {release.archive_password}
                            </TechnicalText>
                            <button
                              className="btn btn-ghost btn-sm"
                              type="button"
                              onClick={() =>
                                handleCopy(
                                  release.archive_password,
                                  'رمز فایل'
                                )
                              }
                            >
                              {copiedText === release.archive_password ? (
                                <Check className="w-3.5 h-3.5 text-emerald-400" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                              <span>کپی رمز</span>
                            </button>
                          </div>
                        </div>
                      )}

                      <div className="drawer-sec">
                        <h3>
                          {item.game_releases.length > 1
                            ? `پارت‌های آرشیو ${toFaDigits(relIdx + 1)}`
                            : 'پارت‌های دانلود'}
                        </h3>
                        <GamePartList
                          parts={release.parts}
                          hasMissingParts={release.has_missing_parts}
                          missingPartNumbers={release.missing_part_numbers}
                          releaseId={release.id}
                        />
                      </div>
                    </React.Fragment>
                  ))
                ) : (
                  <div className="drawer-sec">
                    <p className="text-sm text-zinc-400">لینکی برای این بازی یافت نشد.</p>
                  </div>
                )}

                {item.page_url && (
                  <div className="drawer-sec">
                    <h3>سایت مرجع</h3>
                    <a
                      href={item.page_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-ghost btn-sm inline-flex items-center gap-2"
                    >
                      <span>مشاهده در سایت {item.source_id}</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                )}
              </>
            ) : (
            <>
              <div className="drawer-sec">
                <h3>آرشیو</h3>
                <dl className="kv">
                  <dt>گروه انتشار</dt>
                  <dd>
                    <TechnicalText>{(item as CatalogGame).releaseGroup}</TechnicalText>
                  </dd>
                  <dt>نسخه</dt>
                  <dd>
                    <TechnicalText>{(item as CatalogGame).version}</TechnicalText>
                  </dd>
                  <dt>تعداد پارت</dt>
                  <dd>{toFaDigits((item as CatalogGame).parts.length)} پارت</dd>
                  <dt>حجم کل</dt>
                  <dd>
                    <TechnicalText>
                      {fmtMiB((item as CatalogGame).totalBytes)}
                    </TechnicalText>{' '}
                    <span style={{ color: 'var(--muted-2)' }}>(تخمینی)</span>
                  </dd>
                </dl>
              </div>

              <div className="drawer-sec">
                <h3>استخراج</h3>
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
                      رمز استخراج آرشیو
                    </span>
                    <TechnicalText as="code">
                      {(item as CatalogGame).password}
                    </TechnicalText>
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
                      <span>کپی رمز</span>
                    </button>
                  </div>
                ) : (
                  <div className="notice">
                    <Lock className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>این انتشار رمز آرشیو ندارد.</span>
                  </div>
                )}
              </div>

              <div className="drawer-sec">
                <h3>پارت‌ها به ترتیب</h3>
                <table className="vtable">
                  <thead>
                    <tr>
                      <th>بخش</th>
                      <th>حجم</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {(item as CatalogGame).parts.map((p) => (
                      <tr key={p.n}>
                        <td className="num" style={{ width: '64px' }}>
                          پارت {toFaDigits(p.n)}
                        </td>
                        <td className="num">
                          <TechnicalText>{fmtMiB(p.bytes)}</TechnicalText>{' '}
                          <span style={{ color: 'var(--muted-2)' }}>(تخمینی)</span>
                        </td>
                        <td style={{ textAlign: 'end' }}>
                          <a
                            className="btn btn-ghost btn-sm"
                            href="#"
                            onClick={(e) => handleDownloadClick(e, `پارت ${p.n}`)}
                          >
                            دریافت پارت
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
                    کپی همه لینک‌ها
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
                  لینک‌های کپی‌شده هر کدام در یک خط و به ترتیب پارت ۱ تا پارت N هستند — مستقیماً در
                  Free Download Manager، JDownloader یا wget بچسبانید.
                </p>
              </div>

              <div className="drawer-sec">
                <h3>منابع پشتیبان</h3>
                <div className="prov">
                  <span className="led ok"></span>
                  <strong style={{ color: '#e8e8e8' }}>YasDL</strong>
                  <span>سطح ۱</span>
                  <span style={{ color: 'var(--muted-2)' }}>
                    پارت‌های مرتب + رمز در صفحه
                  </span>
                </div>
                <div className="prov">
                  <span className="led ok"></span>
                  <strong style={{ color: '#e8e8e8' }}>Downloadha</strong>
                  <span>سطح ۲</span>
                  <span style={{ color: 'var(--muted-2)' }}>آینه جایگزین</span>
                </div>
              </div>
            </>
          )
        )}

          {/* MUSIC BODY */}
          {category === 'music' && !isMedia && (
            <>
              <div className="drawer-sec">
                <h3>پیش‌نمایش</h3>
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
                    انتشار MusicBrainz{' '}
                    <TechnicalText>{(item as CatalogMusic).mbid}</TechnicalText> · حجم‌ها
                    بر اساس مدت‌زمان واقعی هر قطعه محاسبه می‌شود، نه ذخیره‌شده.
                  </div>
                </div>
              </div>

              <div className="drawer-sec">
                <h3>قطعات</h3>
                <table className="vtable">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>عنوان</th>
                      <th>128k</th>
                      <th>320k</th>
                      <th>دریافت</th>
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
                          <TechnicalText className="text-xs">
                            {Math.floor(t.sec / 60)}:
                            {String(t.sec % 60).padStart(2, '0')}
                          </TechnicalText>
                        </td>
                        <td className="num">
                          <TechnicalText>{fmtMiB(t.lo)}</TechnicalText>
                        </td>
                        <td className="num">
                          <TechnicalText>{fmtMiB(t.hi)}</TechnicalText>
                        </td>
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
                <h3>منابع پشتیبان</h3>
                <div className="prov">
                  <span className="led ok"></span>
                  <strong style={{ color: '#e8e8e8' }}>Nex1Music</strong>
                  <span>سطح ۱</span>
                  <span style={{ color: 'var(--muted-2)' }}>
                    کیفیت‌های 128/320 برای هر قطعه
                  </span>
                </div>
                <div className="prov">
                  <span className="led ok"></span>
                  <strong style={{ color: '#e8e8e8' }}>Pop-Music</strong>
                  <span>سطح ۲</span>
                  <span style={{ color: 'var(--muted-2)' }}>متمرکز بر آلبوم</span>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer action row: like/unlike plus the Undo window for that action. */}
        {onToggleFavorite && (
          <div className="drawer-foot">
            <button
              className="btn btn-ghost"
              type="button"
              aria-pressed={isItemFavorite?.(item.id) ?? false}
              aria-label={
                (isItemFavorite?.(item.id) ?? false)
                  ? `حذف ${item.title} از علاقه‌مندی‌ها`
                  : `افزودن ${item.title} به علاقه‌مندی‌ها`
              }
              onClick={handleToggleFavorite}
            >
              <Heart
                className={`w-4 h-4 ${
                  (isItemFavorite?.(item.id) ?? false) ? 'fill-current text-rose-400' : ''
                }`}
              />
              <span>
                {(isItemFavorite?.(item.id) ?? false)
                  ? 'حذف از علاقه‌مندی‌ها'
                  : 'افزودن به علاقه‌مندی‌ها'}
              </span>
            </button>

            {lastAction && (
              <button
                className="btn btn-quiet btn-sm"
                type="button"
                onClick={handleUndo}
              >
                <Undo2 className="w-3.5 h-3.5" />
                <span>بازگردانی</span>
              </button>
            )}

            {persistenceBlocked && (
              <span className="hint" role="status">
                علاقه‌مندی‌ها در حالت ناشناس ذخیره نمی‌شوند.
              </span>
            )}
          </div>
        )}
      </aside>
    </>
  )
}
