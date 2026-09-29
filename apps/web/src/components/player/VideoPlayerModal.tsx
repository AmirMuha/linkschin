'use client'

import React, { useRef, useEffect } from 'react'
import { X } from 'lucide-react'

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
          className="w-full h-full object-contain"
        >
          مرورگر شما از پخش مستقیم این ویدیو پشتیبانی نمی‌کند.
        </video>
      </div>
    </dialog>
  )
}
