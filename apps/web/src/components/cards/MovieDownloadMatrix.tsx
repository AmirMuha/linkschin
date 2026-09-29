'use client'

import React, { useState } from 'react'
import type { MovieDownloadVariant } from '@/types/media'
import { Download, Copy, Check } from 'lucide-react'
import { copyToClipboard } from '@/lib/clipboard'
import { useToast } from '@/components/ui/ToastNotification'
import { TechnicalText } from '@/components/ui/TechnicalText'

interface MovieDownloadMatrixProps {
  variants: MovieDownloadVariant[]
}

export function MovieDownloadMatrix({ variants }: MovieDownloadMatrixProps) {
  const { showToast } = useToast()
  const [copiedId, setCopiedId] = useState<string | null>(null)

  if (!variants || variants.length === 0) {
    return (
      <div className="text-xs text-zinc-500 py-2">
        لینکی برای دانلود مستقیم یافت نشد.
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
      <div className="flex flex-col gap-1.5 max-h-60 overflow-y-auto pe-1">
        {variants.map((v) => {
          const isCopied = copiedId === v.id
          const sizeStr = v.file_size_mb
            ? v.file_size_mb > 1024
              ? `${(v.file_size_mb / 1024).toFixed(1)} GB`
              : `${Math.round(v.file_size_mb)} MB`
            : null

          return (
            <div
              key={v.id}
              className="flex items-center justify-between gap-3 p-2 rounded-xl bg-zinc-800/50 border border-zinc-700/50 hover:bg-zinc-800 transition-colors text-xs"
            >
              {/* Quality & Specs */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className="px-2 py-0.5 rounded-md bg-cyan-500/20 text-cyan-300 font-bold font-mono">
                  {v.quality}
                </span>

                {v.codec && (
                  <TechnicalText className="text-zinc-400 text-2xs">
                    {v.codec}
                  </TechnicalText>
                )}

                {v.audio_track && (
                  <span className="text-zinc-300 bg-zinc-700/40 px-1.5 py-0.5 rounded">
                    {v.audio_track}
                  </span>
                )}

                {sizeStr && (
                  <TechnicalText className="text-zinc-500 text-2xs">
                    {sizeStr}
                  </TechnicalText>
                )}
              </div>

              {/* Action buttons: Copy & Direct Download */}
              <div className="flex items-center gap-1 shrink-0">
                <button
                  type="button"
                  onClick={() => handleCopy(v.download_url, v.id)}
                  title="کپی لینک مستقیم"
                  aria-label="کپی لینک مستقیم"
                  className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-700/60 transition-colors"
                >
                  {isCopied ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>

                <a
                  href={v.download_url}
                  download
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-cyan-500/10 hover:bg-cyan-500 text-cyan-400 hover:text-slate-950 font-medium transition-all"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>دانلود</span>
                </a>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
