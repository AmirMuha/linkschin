'use client'

import React, { useState } from 'react'
import type { MediaItem } from '@/types/media'
import { Music, Play, Pause, ExternalLink } from 'lucide-react'
import { useAudioPlayer } from '@/context/AudioPlayerContext'
import { MusicDownloadRow } from './MusicDownloadRow'
import { TechnicalText } from '@/components/ui/TechnicalText'

interface MusicCardProps {
  item: MediaItem
}

export function MusicCard({ item }: MusicCardProps) {
  const [imageError, setImageError] = useState(false)
  const { currentTrack, isPlaying, play, togglePlay } = useAudioPlayer()

  const primaryTrack = item.music_tracks?.[0]
  const isCurrent = primaryTrack && currentTrack?.id === primaryTrack.id
  const isTrackPlaying = isCurrent && isPlaying
  const hasStream = Boolean(primaryTrack?.stream_url)
  // A reference result is link-out only. SC-003: the player and the download
  // row must be ABSENT from the DOM, not hidden — so they are never rendered.
  const isReference = item.source_kind === 'reference'

  function handlePlayToggle() {
    if (!primaryTrack || !hasStream) return
    if (isCurrent) {
      togglePlay()
    } else {
      play(primaryTrack)
    }
  }

  return (
    <article
      className={`group relative flex flex-col rounded-3xl bg-zinc-900/70 border p-4 transition-all hover:shadow-2xl hover:shadow-cyan-950/20 backdrop-blur-md overflow-hidden ${
        isCurrent
          ? 'border-cyan-500/60 shadow-[0_0_20px_rgba(6,182,212,0.15)]'
          : 'border-zinc-800/80 hover:border-zinc-700/80'
      }`}
    >
      {/* Cover / Track Image */}
      <div className="relative w-full aspect-square rounded-2xl overflow-hidden bg-zinc-800/80 mb-4">
        {item.poster_url && !imageError ? (
          <img
            src={item.poster_url}
            alt={item.title}
            onError={() => setImageError(true)}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center text-zinc-600 gap-2">
            <Music className="w-12 h-12" />
            <span className="text-xs">بدون تصویر</span>
          </div>
        )}

        {/* Center Play Button Overlay — omitted entirely for reference items */}
        {!isReference && (
          <button
            type="button"
            onClick={handlePlayToggle}
            disabled={!hasStream}
            title={hasStream ? (isTrackPlaying ? 'توقف پخش' : 'پخش آنلاین') : 'پیش‌نمایش آنلاین در دسترس نیست'}
            aria-label={hasStream ? (isTrackPlaying ? 'توقف پخش' : 'پخش آنلاین') : 'پیش‌نمایش آنلاین در دسترس نیست'}
            className={`absolute inset-0 m-auto w-14 h-14 rounded-full flex items-center justify-center shadow-2xl transition-all backdrop-blur-sm ${
              hasStream
                ? isTrackPlaying
                  ? 'bg-cyan-400 text-slate-950 scale-105'
                  : 'bg-cyan-500/90 hover:bg-cyan-400 text-slate-950 hover:scale-110 opacity-90 group-hover:opacity-100'
                : 'bg-zinc-800/60 text-zinc-500 cursor-not-allowed opacity-40'
            }`}
          >
            {isTrackPlaying ? (
              <Pause className="w-6 h-6 fill-slate-950" />
            ) : (
              <Play className="w-6 h-6 fill-slate-950 ms-0.5" />
            )}
          </button>
        )}

        {/* Source Badge — the kind is text, not colour alone */}
        <div className="absolute top-2.5 start-2.5 flex items-center gap-1 px-2.5 py-1 rounded-full bg-zinc-950/80 border border-zinc-800/80 text-2xs text-zinc-300 font-medium backdrop-blur-md">
          <span>{item.source_id}</span>
          {isReference && <span className="text-violet-300">ارجاعی</span>}
        </div>
      </div>

      {/* Title & Artist */}
      <div className="flex flex-col gap-1 mb-2">
        <h3 className="font-bold text-base text-zinc-100 line-clamp-1" title={item.title}>
          {item.title}
        </h3>

        {primaryTrack?.artist && (
          <div className="text-sm text-cyan-400 font-medium line-clamp-1">
            {primaryTrack.artist}
          </div>
        )}

        {primaryTrack?.album && (
          <div className="text-xs text-zinc-500 line-clamp-1">
            آلبوم: {primaryTrack.album}
          </div>
        )}
      </div>

      {/* Source page link — the reference card's primary, deliberate action */}
      <a
        href={item.page_url}
        target="_blank"
        rel="noopener noreferrer"
        className={`inline-flex items-center gap-1 text-2xs transition-colors self-start mb-2 ${
          isReference
            ? 'font-semibold text-violet-300 hover:text-violet-200'
            : 'text-zinc-500 hover:text-cyan-400'
        }`}
      >
        <span>{isReference ? 'گوش دادن در سایت منبع' : 'مشاهده در سایت مرجع'}</span>
        <ExternalLink className="w-3 h-3" />
      </a>

      {/* Bitrate Download Row — reference items never get one (SC-003) */}
      {!isReference && primaryTrack && (
        <div className="mt-auto border-t border-zinc-800/80 pt-2">
          <MusicDownloadRow downloads={primaryTrack.downloads} />
        </div>
      )}
    </article>
  )
}
