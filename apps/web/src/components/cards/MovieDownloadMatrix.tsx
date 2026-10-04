'use client'

import React, { useState } from 'react'
import type { MovieDownloadVariant } from '@/types/media'
import { Download, Copy, Check } from 'lucide-react'
import { copyToClipboard } from '@/lib/clipboard'
import { variantsForCensorship, variantsForTier } from '@/lib/filters'
import type { CensorshipFilter, TierFilter } from '@/lib/urlFilters'
import { useToast } from '@/components/ui/ToastNotification'
import { TechnicalText } from '@/components/ui/TechnicalText'
import { AccessBadge } from '@/components/ui/AccessBadge'

interface MovieDownloadMatrixProps {
  variants: MovieDownloadVariant[]
  activeTierFilter?: TierFilter
  activeCensorshipFilter?: CensorshipFilter
}

export function MovieDownloadMatrix({
  variants,
  activeTierFilter = 'all',
  activeCensorshipFilter = 'all',
}: MovieDownloadMatrixProps) {
  const { showToast } = useToast()
  const [copiedId, setCopiedId] = useState<string | null>(null)

  // Freemium sources keep their free rows under "free only"; mixed releases keep the
  // rows matching the active censorship filter.
  const visible = variantsForCensorship(
    variantsForTier(variants || [], activeTierFilter),
    activeCensorshipFilter
  )

  if (!variants || variants.length === 0) {
    return (
      <div className="text-xs text-zinc-500 py-2">
        لینکی برای دانلود مستقیم یافت نشد.
      </div>
    )
  }

  if (visible.length === 0) {
    return (
      <div className="text-xs text-zinc-500 py-2">
        هیچ لینکی با فیلترهای فعلی مطابقت ندارد.
      </div>
    )
  }

  async function handleCopy(url: string, id: string) {
    const ok = await copyToClipboard(url)
    if (ok) {
      setCopiedId(id)
      showToast('لینک دانلود کپی شد', 'success')
      setTimeout(() => setCopiedId(null), 2000)
    } else {
      showToast('خطا در کپی لینک', 'error')
    }
  }

  return (
    <div className="flex flex-col gap-2 w-full pt-2">
      <div className="text-xs font-semibold text-zinc-400">لینک‌های دانلود مستقیم:</div>
      <div className="max-h-60 overflow-y-auto pe-1">
        <table className="vtable">
          <tbody>
            {visible.map((v) => {
              const isCopied = copiedId === v.id
              const sizeStr = v.file_size_mb
                ? v.file_size_mb > 1024
                  ? `${(v.file_size_mb / 1024).toFixed(1)} GB`
                  : `${Math.round(v.file_size_mb)} MB`
                : null

              return (
                <tr key={v.id}>
                  <td className="res">{v.quality}</td>
                  <td>
                    {v.codec && <span className="tag tech-text">{v.codec}</span>}{' '}
                    {v.audio_track && <span className="tag">{v.audio_track}</span>}{' '}
                    {v.is_censored === true && <span className="tag" style={{ color: 'var(--warn)' }}>سانسور</span>}{' '}
                    {v.is_censored === false && <span className="tag" style={{ color: 'var(--ok)' }}>کامل</span>}{' '}
                    {v.is_premium && <span className="tag" style={{ color: 'var(--warn)' }}>VIP</span>}
                    <AccessBadge access={v.access} />
                  </td>
                  <td className="num tech-text">{sizeStr}</td>
                  <td style={{ textAlign: 'end', whiteSpace: 'nowrap' }}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', justifyContent: 'flex-end' }}>
                      <button
                        type="button"
                        onClick={() => handleCopy(v.download_url, v.id)}
                        title="کپی لینک مستقیم"
                        aria-label="کپی لینک مستقیم"
                        className="btn btn-quiet btn-sm"
                        style={{ padding: '0 10px', minHeight: '32px' }}
                      >
                        {isCopied ? (
                          <Check className="w-3.5 h-3.5" style={{ color: 'var(--ok)' }} />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>

                      <a
                        href={v.download_url}
                        download
                        rel="noopener noreferrer"
                        className="btn btn-primary btn-sm"
                        style={{ padding: '0 10px', minHeight: '32px' }}
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>دریافت</span>
                      </a>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
