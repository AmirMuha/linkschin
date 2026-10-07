'use client'

import React, { useState, useRef, useEffect } from 'react'
import type { SourceStatus } from '@/types/media'
import { AlertTriangle, X, Radio, ChevronDown, Film, Gamepad2, Music, Eye, EyeOff, RotateCcw } from 'lucide-react'
import { toFaDigits } from '@/lib/format'

interface SourceStatusBarProps {
  sources: SourceStatus[]
  warnings?: string[]
  /** Per-user hidden set (persisted locally, never sent to the server). */
  hiddenSources?: string[]
  onToggleHidden?: (id: string) => void
  onRestoreAllSources?: () => void
}

const CATEGORY_CONFIG: {
  id: string
  label: string
  icon: React.ComponentType<{ className?: string }>
}[] = [
  { id: 'movies', label: 'فیلم و سریال', icon: Film },
  { id: 'games', label: 'بازی‌ها', icon: Gamepad2 },
  { id: 'music', label: 'موسیقی', icon: Music },
]

/**
 * `status` is optional on the wire (sources contract G4), so fall back to
 * deriving it from `enabled`. Kind and status are always returned as TEXT —
 * colour is decoration, never the only signal.
 */
export function describeSource(s: SourceStatus): {
  status: 'active' | 'degraded' | 'inactive'
  statusLabel: string
  reason: string | null
} {
  const status: 'active' | 'degraded' | 'inactive' =
    s.status ?? (s.enabled ? 'active' : 'inactive')
  const statusLabel =
    status === 'active' ? 'فعال' : status === 'degraded' ? 'افت کیفیت' : 'غیرفعال'
  return { status, statusLabel, reason: s.inactive_reason ?? null }
}

export function SourceStatusBar({
  sources,
  warnings = [],
  hiddenSources = [],
  onToggleHidden,
  onRestoreAllSources,
}: SourceStatusBarProps) {
  const [dismissedWarnings, setDismissedWarnings] = useState<Record<number, boolean>>({})
  const [showSourcesMenu, setShowSourcesMenu] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  const activeWarnings = warnings.filter((_, idx) => !dismissedWarnings[idx])
  const enabledCount = sources.filter((s) => s.enabled).length
  const activeCount = sources.filter((s) => describeSource(s).status === 'active').length
  const canHide = Boolean(onToggleHidden)

  // Auto-dismiss warnings; a new warning set restarts the timers from scratch.
  useEffect(() => {
    if (warnings.length === 0) return
    setDismissedWarnings({})
    const timers = warnings.map((_, idx) =>
      setTimeout(() => setDismissedWarnings((prev) => ({ ...prev, [idx]: true })), 6000)
    )
    return () => timers.forEach(clearTimeout)
  }, [warnings])

  // Clickaway and Escape key listener
  useEffect(() => {
    if (!showSourcesMenu) return

    function handlePointerDown(e: MouseEvent | TouchEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowSourcesMenu(false)
      }
    }

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setShowSourcesMenu(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('touchstart', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('touchstart', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [showSourcesMenu])

  return (
    <div className="flex items-center gap-2">
      {/* Upstream Warnings Bar */}
      {activeWarnings.length > 0 && (
        <div className="fixed top-14 inset-x-4 max-w-xl mx-auto z-50 flex flex-col gap-1.5">
          {warnings.map((warning, idx) => {
            if (dismissedWarnings[idx]) return null
            return (
              <div
                key={idx}
                className="flex items-center justify-between gap-3 px-3.5 py-2 rounded-xl bg-rose-950/90 border border-rose-500/40 text-rose-100 text-xs font-medium shadow-xl backdrop-blur-md animate-in fade-in slide-in-from-top-2"
                role="alert"
              >
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-rose-400" />
                  <span>{warning}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setDismissedWarnings((prev) => ({ ...prev, [idx]: true }))}
                  className="p-1 rounded-md hover:bg-rose-500/20 text-rose-400 transition-colors"
                  aria-label="بستن هشدار"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            )
          })}
        </div>
      )}

      {/* Compact Status Pill with Dropdown */}
      {sources.length > 0 && (
        <div ref={menuRef} className="relative">
          <button
            type="button"
            onClick={() => setShowSourcesMenu((prev) => !prev)}
            aria-expanded={showSourcesMenu}
            aria-haspopup="true"
            className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.06] hover:bg-white/[0.12] border border-white/10 hover:border-white/20 text-zinc-300 text-xs font-medium transition-all backdrop-blur-sm cursor-pointer"
          >
            <span
              className={`w-2 h-2 rounded-full shrink-0 animate-pulse ${
                activeCount > 0 ? 'bg-emerald-400' : 'bg-rose-500'
              }`}
            />
            <span>{toFaDigits(enabledCount)} منبع متصل</span>
            {hiddenSources.length > 0 && (
              <span
                className="flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 text-2xs"
                title="منابع پنهان‌شده در نتایج"
              >
                <EyeOff className="w-3 h-3" aria-hidden="true" />
                <span>{toFaDigits(hiddenSources.length)}</span>
              </span>
            )}
            <ChevronDown className={`w-3.5 h-3.5 text-zinc-400 transition-transform duration-200 ${showSourcesMenu ? 'rotate-180 text-zinc-200' : ''}`} />
          </button>

          {showSourcesMenu && (
            <div
              className="absolute end-0 top-full mt-2 w-72 max-h-[26rem] overflow-y-auto p-2.5 rounded-xl bg-[#0e0e0e]/95 border border-white/10 shadow-2xl z-50 flex flex-col gap-2.5 text-xs backdrop-blur-xl animate-in fade-in slide-in-from-top-1"
              role="dialog"
              aria-label="وضعیت و پنهان‌سازی منابع"
            >
              <div className="px-2 py-1 text-2xs text-zinc-400 font-semibold border-b border-white/10 flex items-center justify-between gap-2 sticky top-0 bg-[#0e0e0e]/95 backdrop-blur-md z-10">
                <span>وضعیت منابع سایت‌ها</span>
                <div className="flex items-center gap-2">
                  {canHide && hiddenSources.length > 0 && (
                    <button
                      type="button"
                      onClick={onRestoreAllSources}
                      className="flex items-center gap-1 text-2xs text-zinc-400 hover:text-cyan-400 transition-colors"
                    >
                      <RotateCcw className="w-3 h-3" aria-hidden="true" />
                      <span>بازگردانی همه</span>
                    </button>
                  )}
                  <div className="flex items-center gap-1 text-emerald-400">
                    <Radio className="w-3 h-3" />
                    <span>{toFaDigits(enabledCount)} فعال</span>
                  </div>
                </div>
              </div>

              {canHide && (
                <p className="px-2 text-2xs text-zinc-500 leading-relaxed">
                  با زدن آیکن چشم، نتایج آن منبع در جستجوهای بعدی پنهان می‌شود.
                </p>
              )}

              {/* Categorized Sources Sections */}
              {CATEGORY_CONFIG.map((cat) => {
                const catSources = sources.filter((s) => s.category === cat.id)
                if (catSources.length === 0) return null
                const Icon = cat.icon
                const catEnabledCount = catSources.filter((s) => s.enabled).length

                return (
                  <div key={cat.id} className="flex flex-col gap-1">
                    {/* Category Header */}
                    <div className="flex items-center justify-between px-2 py-1 rounded-md bg-white/[0.04] text-2xs font-semibold text-zinc-300">
                      <div className="flex items-center gap-1.5">
                        <Icon className="w-3 h-3 text-cyan-400" />
                        <span>{cat.label}</span>
                      </div>
                      <span className="text-zinc-500">
                        {toFaDigits(catEnabledCount)} از {toFaDigits(catSources.length)}
                      </span>
                    </div>

                    {/* Source Rows */}
                    <div className="flex flex-col gap-0.5">
                      {catSources.map((s) => {
                        const { status, statusLabel, reason } = describeSource(s)
                        const isReference = s.kind === 'reference'
                        const hidden = hiddenSources.includes(s.id)
                        // A degraded/inactive source offers no hide control: hiding it
                        // would not change the results the user is already missing.
                        const blocked = status === 'degraded' || status === 'inactive'
                        return (
                          <div
                            key={s.id}
                            className="flex flex-col gap-0.5 px-2.5 py-1.5 rounded-lg hover:bg-zinc-800/60 transition-colors"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <span
                                className={`text-xs font-medium truncate ${
                                  hidden ? 'text-zinc-500 line-through' : 'text-zinc-200'
                                }`}
                              >
                                {s.name}
                              </span>
                              <span className="flex items-center gap-1 shrink-0">
                                {canHide && !blocked && (
                                  <button
                                    type="button"
                                    onClick={() => onToggleHidden?.(s.id)}
                                    aria-pressed={hidden}
                                    aria-label={
                                      hidden
                                        ? `نمایش نتایج ${s.name}`
                                        : `پنهان‌کردن نتایج ${s.name}`
                                    }
                                    title={hidden ? 'نمایش در نتایج' : 'پنهان‌کردن از نتایج'}
                                    className={`p-1 rounded-md transition-colors ${
                                      hidden
                                        ? 'text-zinc-500 hover:text-cyan-400 hover:bg-zinc-800'
                                        : 'text-zinc-400 hover:text-cyan-400 hover:bg-zinc-800'
                                    }`}
                                  >
                                    {hidden ? (
                                      <EyeOff className="w-3.5 h-3.5" aria-hidden="true" />
                                    ) : (
                                      <Eye className="w-3.5 h-3.5" aria-hidden="true" />
                                    )}
                                  </button>
                                )}
                                <span
                                  className="text-2xs px-1.5 py-0.5 rounded-md bg-zinc-900 text-zinc-400 border border-zinc-800"
                                  title={isReference ? 'ارجاعی — فقط لینک صفحه' : (s.is_streaming ? 'استریم' : 'مستقیم — پخش و دانلود')}
                                >
                                  {isReference ? 'ارجاعی' : (s.is_streaming ? 'استریم' : 'مستقیم')}
                                </span>
                                {s.access_tier !== 'free' && (
                                  <span
                                    className={`text-2xs px-1.5 py-0.5 rounded-md ${
                                      s.access_tier === 'premium'
                                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                                        : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                                    }`}
                                    title={s.access_tier === 'premium' ? 'فقط با خرید اشتراک سایت منبع' : 'شامل لینک‌های رایگان و پولی'}
                                  >
                                    {s.access_tier === 'premium' ? 'VIP' : 'رایگان و VIP'}
                                  </span>
                                )}
                                <span
                                  className={`text-2xs px-1.5 py-0.5 rounded-md ${
                                    status === 'active'
                                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                      : status === 'degraded'
                                        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                        : 'bg-zinc-900 text-zinc-500 border border-zinc-800'
                                  }`}
                                >
                                  {statusLabel}
                                </span>
                              </span>
                            </div>

                            {/* Reason is required whenever status is not active (G3) */}
                            {status !== 'active' && reason && (
                              <p className="text-2xs text-zinc-500 leading-relaxed">
                                {reason}
                                {typeof s.consecutive_failures === 'number' &&
                                  s.consecutive_failures > 0 && (
                                    <span className="font-mono">
                                      {' '}
                                      ({s.consecutive_failures} جستجوی ناموفق پیاپی)
                                    </span>
                                  )}
                              </p>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
