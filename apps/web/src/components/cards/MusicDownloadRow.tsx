'use client'

import React, { useState } from 'react'
import type { MusicDownloadVariant } from '@/types/media'
import { Download, Copy, Check } from 'lucide-react'
import { copyToClipboard } from '@/lib/clipboard'
import { useToast } from '@/components/ui/ToastNotification'
import { TechnicalText } from '@/components/ui/TechnicalText'
import { AccessBadge } from '@/components/ui/AccessBadge'

interface MusicDownloadRowProps {
  downloads: MusicDownloadVariant[]
}

export function MusicDownloadRow({ downloads }: MusicDownloadRowProps) {
  const { showToast } = useToast()
  const [copiedBitrate, setCopiedBitrate] = useState<string | null>(null)

  if (!downloads || downloads.length === 0) return null

  async function handleCopy(url: string, bitrate: string) {
    const ok = await copyToClipboard(url)
    if (ok) {
      setCopiedBitrate(bitrate)
      showToast(`لینک کیفیت ${bitrate} کپی شد`, 'success')
      setTimeout(() => setCopiedBitrate(null), 2000)
    } else {
      showToast('خطا در کپی لینک دانلود', 'error')
    }
  }

  return (
    <div className="flex items-center flex-wrap gap-2 w-full pt-2">
      <span className="text-2xs font-semibold text-zinc-400">کیفیت‌های دانلود:</span>
      <div className="flex items-center flex-wrap gap-2">
        {downloads.map((dl) => {
          const isCopied = copiedBitrate === dl.bitrate

          return (
            <div
              key={dl.bitrate}
              className="flex items-center gap-1.5 p-1 ps-2.5 rounded-xl bg-zinc-800/60 border border-zinc-700/60 hover:bg-zinc-800 transition-colors text-xs"
            >
              <div className="flex items-center gap-1">
                <span className="font-mono font-bold text-cyan-300 text-xs">
                  {dl.bitrate}
                </span>

                {dl.file_size && (
                  <TechnicalText className="text-zinc-500 text-2xs">
                    ({dl.file_size})
                  </TechnicalText>
                )}

                <AccessBadge access={dl.access} />
              </div>

              <div className="flex items-center gap-0.5">
                <button
                  type="button"
                  onClick={() => handleCopy(dl.download_url, dl.bitrate)}
                  title={`کپی لینک کیفیت ${dl.bitrate}`}
                  aria-label={`کپی لینک کیفیت ${dl.bitrate}`}
                  className="p-1 rounded-md text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700/60 transition-colors"
                >
                  {isCopied ? (
                    <Check className="w-3 h-3 text-emerald-400" />
                  ) : (
                    <Copy className="w-3 h-3" />
                  )}
                </button>

                <a
                  href={dl.download_url}
                  download
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-cyan-500/10 hover:bg-cyan-500 text-cyan-400 hover:text-slate-950 font-medium transition-all text-xs"
                >
                  <Download className="w-3 h-3" />
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
