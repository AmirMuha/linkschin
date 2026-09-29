'use client'

import React from 'react'
import { useAudioPlayer } from '@/context/AudioPlayerContext'
import { Play, Pause, Volume2, VolumeX, X, Music } from 'lucide-react'
import { TechnicalText } from '@/components/ui/TechnicalText'

function formatTime(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return '00:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

export function GlobalAudioPlayer() {
  const {
    currentTrack,
    isPlaying,
    currentTime,
    duration,
    volume,
    togglePlay,
    seek,
    setVolume,
    close,
  } = useAudioPlayer()

  if (!currentTrack) return null

  return (
    <div
      role="region"
      aria-label="پخش‌کننده صوتی"
      className="fixed bottom-0 inset-x-0 z-40 px-4 py-3 bg-zinc-950/95 border-t border-zinc-800/80 shadow-2xl backdrop-blur-xl animate-in slide-in-from-bottom-4 transition-all"
    >
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Track Info */}
        <div className="flex items-center gap-3 w-full sm:w-1/4 min-w-0">
          <div className="w-11 h-11 rounded-xl bg-zinc-800 overflow-hidden shrink-0 flex items-center justify-center">
            {currentTrack.cover_url ? (
              <img
                src={currentTrack.cover_url}
                alt={currentTrack.title}
                className="w-full h-full object-cover"
              />
            ) : (
              <Music className="w-5 h-5 text-cyan-400" />
            )}
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-semibold text-zinc-100 truncate" title={currentTrack.title}>
              {currentTrack.title}
            </span>
            <span className="text-xs text-zinc-400 truncate" title={currentTrack.artist}>
              {currentTrack.artist}
            </span>
          </div>
        </div>

        {/* Controls & Scrubber */}
        <div className="flex flex-col items-center gap-1.5 w-full sm:w-2/4">
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={togglePlay}
              className="w-10 h-10 rounded-full bg-cyan-500 hover:bg-cyan-400 text-slate-950 flex items-center justify-center transition-all shadow-[0_0_12px_rgba(6,182,212,0.4)]"
              aria-label={isPlaying ? 'توقف پخش' : 'شروع پخش'}
            >
              {isPlaying ? (
                <Pause className="w-5 h-5 fill-slate-950" />
              ) : (
                <Play className="w-5 h-5 fill-slate-950 ms-0.5" />
              )}
            </button>
          </div>

          <div className="w-full flex items-center gap-2.5 text-xs text-zinc-400">
            <TechnicalText className="text-2xs w-10 text-end">
              {formatTime(currentTime)}
            </TechnicalText>

            <input
              type="range"
              min={0}
              max={duration || 100}
              value={currentTime}
              onChange={(e) => seek(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
              aria-label="نوار زمان آهنگ"
            />

            <TechnicalText className="text-2xs w-10 text-start">
              {formatTime(duration)}
            </TechnicalText>
          </div>
        </div>

        {/* Volume & Close */}
        <div className="hidden sm:flex items-center justify-end gap-3 w-1/4">
          <div className="flex items-center gap-2 text-zinc-400">
            <button
              type="button"
              onClick={() => setVolume(volume > 0 ? 0 : 0.8)}
              aria-label={volume === 0 ? 'فعال کردن صدا' : 'بی‌صدا کردن'}
              className="p-1 hover:text-zinc-200 transition-colors"
            >
              {volume === 0 ? (
                <VolumeX className="w-4 h-4 text-rose-400" />
              ) : (
                <Volume2 className="w-4 h-4" />
              )}
            </button>

            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={volume}
              onChange={(e) => setVolume(parseFloat(e.target.value))}
              className="w-20 h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
              aria-label="بلندی صدا"
            />
          </div>

          <button
            type="button"
            onClick={close}
            aria-label="بستن پخش‌کننده صوتی"
            className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
