'use client'

import React, { useRef, useEffect, useState } from 'react'
import { Loader2, X } from 'lucide-react'

interface VideoPlayerModalProps {
  isOpen: boolean
  streamUrl: string | null
  title: string
  onClose: () => void
}

export function VideoPlayerModal({
  isOpen,
  streamUrl,
  title,
  onClose,
}: VideoPlayerModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  // A multi-hundred-MB stream can sit at readyState 0 for many seconds with nothing
  // on screen; without this the modal reads as broken rather than loading.
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return

    if (isOpen && streamUrl) {
      if (!dialog.open) {
        dialog.showModal()
      }
    } else {
      if (dialog.open) {
        dialog.close()
      }
      if (videoRef.current) {
        videoRef.current.pause()
      }
    }
  }, [isOpen, streamUrl])

  // Each new source restarts the wait.
  useEffect(() => {
    if (isOpen && streamUrl) setStatus('loading')
  }, [isOpen, streamUrl])

  function handleClose() {
    if (videoRef.current) {
      videoRef.current.pause()
    }
    onClose()
  }

  if (!isOpen || !streamUrl) return null

  return (
    <dialog
      ref={dialogRef}
      onClose={handleClose}
      className="m-auto rounded-3xl bg-zinc-950/95 border border-zinc-800 p-0 text-zinc-100 shadow-2xl backdrop:bg-black/80 backdrop:backdrop-blur-sm max-w-4xl w-[95vw] overflow-hidden outline-none"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
        <h3 className="text-base font-semibold truncate pe-4">{title}</h3>
        <button
          type="button"
          onClick={handleClose}
          className="p-1.5 rounded-xl hover:bg-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors"
          aria-label="بستن پنجره پخش ویدیو"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Video Container */}
      <div className="relative aspect-video w-full bg-black">
        <video
          ref={videoRef}
          src={streamUrl}
          controls
          autoPlay
          onCanPlay={() => setStatus('ready')}
          onWaiting={() => setStatus('loading')}
          onPlaying={() => setStatus('ready')}
          onError={() => setStatus('error')}
          className="w-full h-full object-contain"
        >
          مرورگر شما از پخش مستقیم این ویدیو پشتیبانی نمی‌کند.
        </video>

        {status === 'loading' && (
          <div
            role="status"
            aria-live="polite"
            className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-black/60 text-zinc-300"
          >
            <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
            <span className="text-xs">در حال دریافت ویدیو…</span>
          </div>
        )}

        {status === 'error' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/70 px-6 text-center">
            <p className="text-sm font-semibold text-rose-300">پخش این ویدیو ممکن نشد.</p>
            <p className="text-xs text-zinc-400">
              ممکن است لینک منقضی شده باشد. دکمهٔ تازه‌سازی نتایج را بزنید.
            </p>
          </div>
        )}
      </div>
    </dialog>
  )
}