'use client'

import React, { useState } from 'react'
import { useAudioPlayer } from '@/context/AudioPlayerContext'
import {
  Play,
  Pause,
  Volume2,
  Volume1,
  VolumeX,
  X,
  Music,
  SkipBack,
  SkipForward,
  Gauge,
} from 'lucide-react'
import { TechnicalText } from '@/components/ui/TechnicalText'

function formatTime(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return '00:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

/** One icon-only control. Centralised so the player bar has no repeated
 *  44px/focus-ring/label boilerplate across eight buttons. */
function ControlButton({
  onClick,
  label,
  pressed,
  children,
  accent = false,
}: {
  onClick: () => void
  label: string
  pressed?: boolean
  children: React.ReactNode
  accent?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      aria-pressed={pressed}
      className={`w-9 h-9 sm:w-8 sm:h-8 rounded-lg flex items-center justify-center transition-all ${
        accent
          ? pressed
            ? 'bg-cyan-500/20 text-cyan-300'
            : 'text-zinc-400 hover:text-cyan-300 hover:bg-zinc-800'
          : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800'
      }`}
    >
      {children}
    </button>
  )
}

export function GlobalAudioPlayer() {
  const {
    currentTrack,
    isPlaying,
    currentTime,
    duration,
    volume,
    isMuted,
    playbackRate,
    togglePlay,
    seek,
    skip,
    toggleMute,
    cyclePlaybackRate,
    setVolume,
    close,
  } = useAudioPlayer()

  const [expanded, setExpanded] = useState(false)

  if (!currentTrack) return null

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0
  const VolumeIcon = isMuted || volume === 0 ? VolumeX : volume < 0.5 ? Volume1 : Volume2

  return (
    <div
      role="region"
      aria-label="پخش‌کننده صوتی"
      className="fixed bottom-0 inset-x-0 z-40 bg-zinc-950/80 border-t border-zinc-800/80 shadow-[0_-8px_32px_rgba(0,0,0,0.5)] backdrop-blur-2xl animate-in slide-in-from-bottom-4"
    >
      {/* Ambient glow tinted by the cover art. Decorative, so it is hidden from
          the accessibility tree rather than given a label. */}
      <div
        aria-hidden="true"
        className="absolute inset-0 opacity-40 pointer-events-none"
        style={
          currentTrack.cover_url
            ? {
                backgroundImage: `url(${currentTrack.cover_url})`,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                maskImage: 'linear-gradient(to top, black, transparent)',
                WebkitMaskImage: 'linear-gradient(to top, black, transparent)',
              }
            : undefined
        }
      />

      {/* Thin top progress line: the whole bar doubles as the scrubber's track,
          so the fill is visible even when the player's own row is scrolled past. */}
      <div aria-hidden="true" className="h-0.5 bg-zinc-900 overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-cyan-400 to-violet-400 transition-[width] duration-150"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="relative max-w-6xl mx-auto px-4 py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-3">
        {/* Track Info */}
        <div className="flex items-center gap-3 min-w-0 flex-1 sm:flex-none sm:w-1/4">
          <div className="relative w-11 h-11 rounded-xl bg-zinc-800 overflow-hidden shrink-0 flex items-center justify-center ring-1 ring-white/5">
            {currentTrack.cover_url ? (
              <img
                src={currentTrack.cover_url}
                alt={currentTrack.title}
                className="w-full h-full object-cover"
              />
            ) : (
              <Music className="w-5 h-5 text-cyan-400" aria-hidden="true" />
            )}

            {/* Equalizer — only while actually playing, so a paused track does
                not keep bouncing. Falls back to a static bar under
                prefers-reduced-motion. */}
            {isPlaying && (
              <span
                aria-hidden="true"
                className="absolute inset-x-0 bottom-0 flex items-end justify-center gap-[2px] h-3 bg-gradient-to-t from-black/80 to-transparent"
              >
                {[0, 1, 2].map((i) => (
                  <span key={i} className="eq-bar w-[3px] h-full rounded-full bg-cyan-400" />
                ))}
              </span>
            )}
          </div>

          <div className="flex flex-col min-w-0">
            <span className="text-sm font-semibold text-zinc-100 truncate" title={currentTrack.title}>
              {currentTrack.title}
            </span>
            <span className="text-xs text-zinc-400 truncate" title={currentTrack.artist}>
              {currentTrack.artist || 'خواننده نامشخص'}
            </span>
          </div>
        </div>

        {/* Transport & Scrubber */}
        <div className="flex flex-col items-center gap-1 w-full sm:w-2/4">
          <div className="flex items-center gap-1 sm:gap-2">
            <ControlButton onClick={() => skip(-15)} label="۱۵ ثانیه عقب">
              <SkipBack className="w-4 h-4" />
            </ControlButton>

            <button
              type="button"
              onClick={togglePlay}
              aria-label={isPlaying ? 'توقف پخش' : 'شروع پخش'}
              className="w-11 h-11 sm:w-12 sm:h-12 rounded-full bg-cyan-500 hover:bg-cyan-400 active:scale-95 text-slate-950 flex items-center justify-center transition-all shadow-[0_0_20px_rgba(6,182,212,0.45)] hover:shadow-[0_0_28px_rgba(6,182,212,0.6)]"
            >
              {isPlaying ? (
                <Pause className="w-5 h-5 fill-slate-950" aria-hidden="true" />
              ) : (
                <Play className="w-5 h-5 fill-slate-950 ms-0.5" aria-hidden="true" />
              )}
            </button>

            <ControlButton onClick={() => skip(15)} label="۱۵ ثانیه جلو">
              <SkipForward className="w-4 h-4" />
            </ControlButton>

            <ControlButton
              onClick={cyclePlaybackRate}
              label={`سرعت پخش ${playbackRate}×`}
              pressed={playbackRate !== 1}
              accent
            >
              <Gauge className="w-4 h-4" aria-hidden="true" />
            </ControlButton>
          </div>

          <div className="w-full flex items-center gap-2.5 text-xs text-zinc-400">
            <TechnicalText className="text-2xs w-10 text-end tabular-nums">
              {formatTime(currentTime)}
            </TechnicalText>

            <input
              type="range"
              className="range flex-1 h-1.5"
              style={{ '--range-progress': `${progress}%` } as React.CSSProperties}
              min={0}
              max={duration || 100}
              value={currentTime}
              onChange={(e) => seek(parseFloat(e.target.value))}
              aria-label="نوار زمان آهنگ"
              aria-valuetext={`${formatTime(currentTime)} از ${formatTime(duration)}`}
            />

            <TechnicalText className="text-2xs w-10 text-start tabular-nums">
              {formatTime(duration)}
            </TechnicalText>
          </div>

          {playbackRate !== 1 && (
            <span className="text-2xs text-cyan-300 font-medium">{playbackRate}×</span>
          )}
        </div>

        {/* Volume, rate badge & close */}
        <div className="flex items-center justify-between sm:justify-end gap-2 sm:gap-3 sm:w-1/4">
          {/* Volume is collapsed to the icon alone on small screens: a 20rem
              slider plus the transport row would force the bar to wrap. */}
          <div className="flex items-center gap-2 text-zinc-400">
            <ControlButton onClick={toggleMute} label={isMuted || volume === 0 ? 'فعال کردن صدا' : 'بی‌صدا کردن'}>
              <VolumeIcon className={`w-4 h-4 ${isMuted || volume === 0 ? 'text-rose-400' : ''}`} aria-hidden="true" />
            </ControlButton>

            <input
              type="range"
              className="range hidden sm:block w-20 h-1.5"
              style={{ '--range-progress': `${volume * 100}%` } as React.CSSProperties}
              min={0}
              max={1}
              step={0.05}
              value={volume}
              onChange={(e) => setVolume(parseFloat(e.target.value))}
              aria-label="بلندی صدا"
              aria-valuetext={`${Math.round(volume * 100)}٪`}
            />
          </div>

          <button
            type="button"
            onClick={close}
            aria-label="بستن پخش‌کننده صوتی"
            className="w-9 h-9 sm:w-8 sm:h-8 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors flex items-center justify-center"
          >
            <X className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Secondary row: bitrate + album + source link. Toggled rather than
          always-visible so the bar keeps one line on a phone. */}
      <div className="relative max-w-6xl mx-auto px-4 pb-2">
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          className="text-2xs text-zinc-500 hover:text-cyan-400 transition-colors"
        >
          {expanded ? 'بستن جزئیات' : 'جزئیات آهنگ'}
        </button>

        {expanded && (
          <div className="mt-2 pt-2 border-t border-zinc-800/80 flex flex-wrap items-center gap-x-4 gap-y-1 text-2xs text-zinc-400 animate-in fade-in slide-in-from-top-1">
            {currentTrack.album && (
              <span>
                آلبوم: <span className="text-zinc-200">{currentTrack.album}</span>
              </span>
            )}
            <span>
              منبع: <span className="text-zinc-200">{currentTrack.source_name}</span>
            </span>
            {currentTrack.downloads.length > 0 && (
              <span>
                کیفیت‌ها:{' '}
                <span className="text-zinc-200">
                  {currentTrack.downloads.map((d) => d.bitrate).join('، ')}
                </span>
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}