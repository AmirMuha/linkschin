'use client'

import React, { useState } from 'react'
import type { GamePartLink } from '@/types/media'
import { Download, Copy, Check, Files, AlertTriangle } from 'lucide-react'
import { copyToClipboard } from '@/lib/clipboard'
import { formatPartLinksForClipboard, sortParts } from '@/lib/archive'
import { useToast } from '@/components/ui/ToastNotification'
import { TechnicalText } from '@/components/ui/TechnicalText'
import { AccessBadge } from '@/components/ui/AccessBadge'
import { toFaDigits } from '@/lib/format'

interface GamePartListProps {
  parts: GamePartLink[]
  hasMissingParts?: boolean
  missingPartNumbers?: number[]
  /** Distinguishes identical part numbers belonging to different archives. */
  releaseId?: string
}

export function GamePartList({
  parts,
  hasMissingParts = false,
  missingPartNumbers = [],
  releaseId = '',
}: GamePartListProps) {
  const { showToast } = useToast()
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)
  const [copiedAll, setCopiedAll] = useState(false)

  const sortedParts = sortParts(parts)

  if (!parts || parts.length === 0) {
    return (
      <div className="text-xs text-zinc-500 py-2">
        لینکی برای دانلود این نسخه ثبت نشده است.
      </div>
    )
  }

  async function handleCopyPart(url: string, index: number) {
    const ok = await copyToClipboard(url)
    if (ok) {
      setCopiedIndex(index)
      showToast('لینک پارت کپی شد', 'success')
      setTimeout(() => setCopiedIndex(null), 2000)
    } else {
      showToast('خطا در کپی لینک پارت', 'error')
    }
  }

  async function handleCopyAll() {
    const batch = formatPartLinksForClipboard(sortedParts)
    const ok = await copyToClipboard(batch)
    if (ok) {
      setCopiedAll(true)
      showToast(`لینک تمام پارت‌ها (${sortedParts.length} پارت) کپی شد`, 'success')
      setTimeout(() => setCopiedAll(false), 2000)
    } else {
      showToast('خطا در کپی تمام لینک‌ها', 'error')
    }
  }

  return (
    <div className="flex flex-col gap-2.5 w-full pt-2">
      {/* Missing Parts Alert */}
      {hasMissingParts && missingPartNumbers.length > 0 && (
        <div
          role="alert"
          className="flex items-center gap-2 p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs"
        >
          <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
          <span>
            توجه: پارت‌های شماره{' '}
            <TechnicalText className="text-amber-200 font-bold">
              {missingPartNumbers.join(', ')}
            </TechnicalText>{' '}
            یافت نشدند.
          </span>
        </div>
      )}

      {/* Batch Copy Trigger */}
      {sortedParts.length > 1 && (
        <div className="flex items-center justify-end pb-1">
          <button
            type="button"
            onClick={handleCopyAll}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-xs font-medium transition-all"
          >
            {copiedAll ? (
              <Check className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <Files className="w-3.5 h-3.5" />
            )}
            <span>کپی تمام پارت‌ها (IDM)</span>
          </button>
        </div>
      )}

      {/* Parts List */}
      <div className="max-h-56 overflow-y-auto pe-1">
        <table className="vtable">
          <tbody>
            {sortedParts.map((part, index) => {
              const isCopied = copiedIndex === index
              const label =
                sortedParts.length === 1
                  ? (!part.part_label || part.part_label === 'Full Game' || /^part\s*1$/i.test(part.part_label)
                      ? 'بازی کامل'
                      : part.part_label)
                  : (/^part\s*\d+$/i.test(part.part_label) || /^پارت\s*\d+$/i.test(part.part_label)
                      ? `پارت ${toFaDigits(part.part_number)}`
                      : part.part_label)

              return (
                <tr
                  key={`${releaseId}:${part.part_number}:${part.download_url}`}
                >
                  <td className="res">
                    <div className="flex items-center gap-2">
                      <span className="text-zinc-200" title={label}>
                        {label}
                      </span>
                      <AccessBadge access={part.access} />
                    </div>
                  </td>
                  <td className="num tech-text">
                    {part.file_size && (
                      <span className="bg-zinc-900/60 px-1.5 py-0.5 rounded">
                        {part.file_size}
                      </span>
                    )}
                  </td>
                  <td style={{ textAlign: 'end', whiteSpace: 'nowrap' }}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', justifyContent: 'flex-end' }}>
                      <button
                        type="button"
                        onClick={() => handleCopyPart(part.download_url, index)}
                        title="کپی لینک پارت"
                        aria-label={`کپی لینک پارت ${part.part_number}`}
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
                        href={part.download_url}
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
