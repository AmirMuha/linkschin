'use client'

import React, { useEffect } from 'react'
import type { MediaItem } from '@/types/media'
import { toFaDigits } from '@/lib/format'
import { copyToClipboard } from '@/lib/clipboard'
import { useToast } from '@/components/ui/ToastNotification'
import { TechnicalText } from '@/components/ui/TechnicalText'
import { X, Play, Copy, Check, Heart, Undo2, ExternalLink } from 'lucide-react'
import { GamePartList } from '@/components/cards/GamePartList'
import { MovieDownloadMatrix } from '@/components/cards/MovieDownloadMatrix'
import { MusicDownloadRow } from '@/components/cards/MusicDownloadRow'
import type { CensorshipFilter, TierFilter } from '@/lib/urlFilters'

export type DrawerItem = MediaItem

interface DetailDrawerProps {
  item: DrawerItem | null
  isOpen: boolean
  onClose: () => void
  onPlayStream?: (url: string, title: string) => void
  onToggleFavorite?: (item: MediaItem) => void
  isItemFavorite?: (id: string) => boolean
  /** Current result filters — prune the movie download rows the way the card used to. */
  activeTierFilter?: TierFilter
  activeCensorshipFilter?: CensorshipFilter
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
  activeTierFilter = 'all',
  activeCensorshipFilter = 'all',
  persistenceBlocked,
}: DetailDrawerProps) {
  const { showToast } = useToast()
  const [copiedText, setCopiedText] = React.useState<string | null>(null)
  const [posterError, setPosterError] = React.useState(false)

  // Each item gets its own poster attempt — a broken one must not hide the next.
  React.useEffect(() => setPosterError(false), [item?.id])
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
    // Only the open item can be undone — the drawer holds the record itself.
    if (!lastAction || !onToggleFavorite || !item || item.id !== lastAction.id) return
    onToggleFavorite(item)
    setLastAction(null)
  }

  const category = item.category
  const releaseGroup = item.game_releases?.[0]?.release_group

  const primaryBadge =
    category === 'games' ? releaseGroup || 'بازی' : category === 'music' ? 'آلبوم' : 'فیلم'

  const categoryBadge =
    category === 'movies' ? 'فیلم' : category === 'games' ? 'بازی' : 'آهنگ'

  const showCategoryBadge = Boolean(categoryBadge && categoryBadge !== primaryBadge)

  // Preview audio: the first track that actually streams, else the item-level stream.
  const previewTrack = item.music_tracks?.find((t) => t.stream_url)
  const previewSrc = previewTrack?.stream_url ?? item.stream_url

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
          {item.poster_url && !posterError && (
            <img
              src={item.poster_url}
              alt={`${item.title} artwork`}
              onError={() => setPosterError(true)}
            />
          )}
        </div>

        <div className="drawer-body" tabIndex={-1}>
          {/* Drawer Header Block */}
          <div className="drawer-head">
            <div className="eyebrow">
              <span className="pill-red">{primaryBadge}</span>
              {showCategoryBadge && (
                <span className="pill-ghost">{categoryBadge}</span>
              )}
              {item.censorship_status === 'censored' && (
                <span className="pill-ghost">نسخه بازبینی‌شده</span>
              )}
              {item.imdb_rating != null && (
                <span className="pill-ghost">IMDb {item.imdb_rating.toFixed(1)}/10</span>
              )}
            </div>

            <h2>{item.title}</h2>

            {item.original_title && (
              <p className="hero-meta" lang="fa" dir="rtl">
                <strong style={{ fontSize: '20px' }}>{item.original_title}</strong>
              </p>
            )}
          </div>

          <p className="hero-desc">{item.description}</p>

          {/* MOVIE BODY */}
          {category === 'movies' && (
            <div className="drawer-sec">
              <h3>کیفیت‌ها و لینک‌های دانلود</h3>
              {item.movie_variants && item.movie_variants.length > 0 ? (
                <MovieDownloadMatrix
                  variants={item.movie_variants}
                  activeTierFilter={activeTierFilter}
                  activeCensorshipFilter={activeCensorshipFilter}
                />
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

              {item.stream_url && (
                <div className="notice" style={{ marginTop: '14px' }}>
                  <Play className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>
                    سایت منبع این عنوان را به‌صورت پخش‌کننده مستقیم ارائه می‌کند، بنابراین
                    پخش‌کننده مرورگر در کنار لینک‌های دانلود نمایش داده می‌شود. هیچ فایلی از
                    این سایت پروکسی نمی‌شود.
                  </span>
                  {onPlayStream && (
                    <button
                      type="button"
                      onClick={() => onPlayStream(item.stream_url!, item.title)}
                      className="btn btn-primary btn-sm"
                      style={{ marginInlineStart: 'auto' }}
                    >
                      پخش در مرورگر
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* GAME BODY */}
          {category === 'games' && (
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
                          <span>رمز استخراج آرشیو</span>
                          <TechnicalText as="code">
                            {release.archive_password}
                          </TechnicalText>
                          <button
                            className="btn btn-ghost btn-sm"
                            type="button"
                            onClick={() =>
                              handleCopy(release.archive_password, 'رمز فایل')
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
                        {release.parts?.length > 0 && (
                          <span className="text-zinc-400 font-normal ms-1">
                            ({toFaDigits(release.parts.length)})
                          </span>
                        )}
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
          )}

          {/* MUSIC BODY */}
          {category === 'music' && (
            <>
              {item.music_tracks && item.music_tracks.length > 0 ? (
                <>
                  <div className="drawer-sec">
                    <h3>پیش‌نمایش</h3>
                    <div className="player">
                      <div className="player-row">
                        {item.poster_url && (
                          <img
                            src={item.poster_url}
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
                        )}
                        <div>
                          <strong style={{ color: '#fff', fontSize: '15px' }}>
                            {item.title}
                          </strong>
                          {previewTrack?.artist && <div>{previewTrack.artist}</div>}
                        </div>
                      </div>
                      {previewSrc && (
                        <audio
                          controls
                          preload="none"
                          src={previewSrc}
                          style={{ width: '100%', marginTop: '10px' }}
                        />
                      )}
                    </div>
                  </div>

                  <div className="drawer-sec">
                    <h3>قطعات</h3>
                    <div style={{ display: 'grid', gap: '12px' }}>
                      {item.music_tracks.map((track, idx) => (
                        <div
                          key={track.id || idx}
                          style={{
                            display: 'grid',
                            gap: '4px',
                            paddingBottom: '10px',
                            borderBottom: '1px solid var(--border)',
                          }}
                        >
                          <div>
                            <span style={{ color: 'var(--muted-2)' }}>
                              {toFaDigits(idx + 1)}.{' '}
                            </span>
                            <strong>{track.title}</strong>
                            {track.album && (
                              <span style={{ color: 'var(--muted-2)' }}> · {track.album}</span>
                            )}
                          </div>
                          <MusicDownloadRow downloads={track.downloads || []} />
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <div className="drawer-sec">
                  <p className="text-sm text-zinc-400">لینکی برای این آهنگ یافت نشد.</p>
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
