'use client'

import React, { createContext, useContext, useState, useRef, useEffect, useCallback } from 'react'
import type { MusicTrack } from '@/types/media'

interface AudioPlayerContextType {
  currentTrack: MusicTrack | null
  isPlaying: boolean
  currentTime: number
  duration: number
  volume: number
  /** Previous volume, restored by the mute toggle. Needed because the slider's
   *  value is the source of truth and a bare `volume > 0 ? 0 : 0.8` loses it. */
  volumeBeforeMute: number
  isMuted: boolean
  isRepeating: boolean
  playbackRate: number
  play: (track: MusicTrack) => void
  togglePlay: () => void
  seek: (seconds: number) => void
  skip: (delta: number) => void
  setVolume: (vol: number) => void
  toggleMute: () => void
  toggleRepeat: () => void
  cyclePlaybackRate: () => void
  close: () => void
}

export const PLAYBACK_RATES = [0.75, 1, 1.25, 1.5, 2] as const
const SKIP_SECONDS = 15

const AudioPlayerContext = createContext<AudioPlayerContextType | undefined>(undefined)

const VOLUME_STORAGE_KEY = 'player_volume'

export function AudioPlayerProvider({ children }: { children: React.ReactNode }) {
  const [currentTrack, setCurrentTrack] = useState<MusicTrack | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolumeState] = useState(0.8)
  const [volumeBeforeMute, setVolumeBeforeMute] = useState(0.8)
  const [playbackRate, setPlaybackRate] = useState(1)
  const [isRepeating, setIsRepeating] = useState(false)

  const audioRef = useRef<HTMLAudioElement | null>(null)

  // Initialize Audio element and restore volume
  useEffect(() => {
    const audio = new Audio()
    audioRef.current = audio

    let initialVol = 0.8
    try {
      const saved = localStorage.getItem(VOLUME_STORAGE_KEY)
      if (saved) {
        const parsed = parseFloat(saved)
        if (!isNaN(parsed) && parsed >= 0 && parsed <= 1) {
          initialVol = parsed
        }
      }
    } catch {
      // Ignore
    }
    audio.volume = initialVol
    setVolumeState(initialVol)
    setVolumeBeforeMute(initialVol)

    const handleTimeUpdate = () => setCurrentTime(audio.currentTime)
    const handleLoadedMetadata = () => setDuration(audio.duration || 0)
    const handleEnded = () => setIsPlaying(false)
    const handlePlay = () => setIsPlaying(true)
    const handlePause = () => setIsPlaying(false)
    const handleError = () => {
      setIsPlaying(false)
    }

    audio.addEventListener('timeupdate', handleTimeUpdate)
    audio.addEventListener('loadedmetadata', handleLoadedMetadata)
    audio.addEventListener('ended', handleEnded)
    audio.addEventListener('play', handlePlay)
    audio.addEventListener('pause', handlePause)
    audio.addEventListener('error', handleError)

    return () => {
      audio.pause()
      audio.removeEventListener('timeupdate', handleTimeUpdate)
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata)
      audio.removeEventListener('ended', handleEnded)
      audio.removeEventListener('play', handlePlay)
      audio.removeEventListener('pause', handlePause)
      audio.removeEventListener('error', handleError)
    }
  }, [])

  const play = useCallback((track: MusicTrack) => {
    const audio = audioRef.current
    if (!audio || !track.stream_url) return

    // If same track, just resume
    if (currentTrack?.id === track.id) {
      audio.play().catch(() => {})
      return
    }

    audio.pause()
    audio.src = track.stream_url
    audio.load()
    setCurrentTrack(track)
    audio.play().catch(() => {})
  }, [currentTrack])

  const togglePlay = useCallback(() => {
    const audio = audioRef.current
    if (!audio || !currentTrack) return

    if (isPlaying) {
      audio.pause()
    } else {
      audio.play().catch(() => {})
    }
  }, [isPlaying, currentTrack])

  const seek = useCallback((seconds: number) => {
    const audio = audioRef.current
    if (!audio) return
    const target = Math.max(0, Math.min(audio.duration || seconds, seconds))
    audio.currentTime = target
    setCurrentTime(target)
  }, [])

  const skip = useCallback((delta: number) => {
    const audio = audioRef.current
    if (!audio) return
    const target = Math.max(0, Math.min(audio.duration || Infinity, audio.currentTime + delta))
    audio.currentTime = target
    setCurrentTime(target)
  }, [])

  const toggleMute = useCallback(() => {
    setVolumeState((current) => {
      // Leaving mute must restore what the user had, not a fixed 0.8.
      if (current > 0) {
        setVolumeBeforeMute(current)
        if (audioRef.current) audioRef.current.volume = 0
        try {
          localStorage.removeItem(VOLUME_STORAGE_KEY)
        } catch {
          // Ignore
        }
        return 0
      }
      const restored = volumeBeforeMute || 0.8
      if (audioRef.current) audioRef.current.volume = restored
      try {
        localStorage.setItem(VOLUME_STORAGE_KEY, restored.toString())
      } catch {
        // Ignore
      }
      return restored
    })
  }, [volumeBeforeMute])

  const toggleRepeat = useCallback(() => {
    setIsRepeating((prev) => {
      const next = !prev
      if (audioRef.current) {
        audioRef.current.loop = next
      }
      return next
    })
  }, [])

  const cyclePlaybackRate = useCallback(() => {
    setPlaybackRate((current) => {
      const next = PLAYBACK_RATES[(PLAYBACK_RATES.indexOf(current as (typeof PLAYBACK_RATES)[number]) + 1) % PLAYBACK_RATES.length]
      if (audioRef.current) audioRef.current.playbackRate = next
      return next
    })
  }, [])

  const setVolume = useCallback((vol: number) => {
    const clamped = Math.max(0, Math.min(1, vol))
    setVolumeState(clamped)
    if (audioRef.current) {
      audioRef.current.volume = clamped
    }
    try {
      localStorage.setItem(VOLUME_STORAGE_KEY, clamped.toString())
    } catch {
      // Ignore
    }
  }, [])

  const close = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.src = ''
    }
    setCurrentTrack(null)
    setIsPlaying(false)
    setCurrentTime(0)
    setDuration(0)
    setPlaybackRate(1)
    if (audioRef.current) audioRef.current.playbackRate = 1
  }, [])

  return (
    <AudioPlayerContext.Provider
      value={{
        currentTrack,
        isPlaying,
        currentTime,
        duration,
        volume,
        volumeBeforeMute,
        isMuted: volume === 0,
        isRepeating,
        playbackRate,
        play,
        togglePlay,
        seek,
        skip,
        setVolume,
        toggleMute,
        toggleRepeat,
        cyclePlaybackRate,
        close,
      }}
    >
      {children}
    </AudioPlayerContext.Provider>
  )
}

export function useAudioPlayer(): AudioPlayerContextType {
  const context = useContext(AudioPlayerContext)
  if (!context) {
    throw new Error('useAudioPlayer must be used within an AudioPlayerProvider')
  }
  return context
}
