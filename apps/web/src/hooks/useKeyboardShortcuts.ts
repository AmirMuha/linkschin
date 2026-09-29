'use client'

import { useEffect } from 'react'

interface ShortcutHandlers {
  onSearchFocus?: () => void
  onEscape?: () => void
}

export function useKeyboardShortcuts({ onSearchFocus, onEscape }: ShortcutHandlers) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null
      const isInput =
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable)

      // Escape key handles blur and modal dismissal
      if (e.key === 'Escape') {
        if (onEscape) {
          onEscape()
        }
        return
      }

      // Cmd+K or Ctrl+K
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        if (onSearchFocus) {
          onSearchFocus()
        }
        return
      }

      // Forward slash '/' when not already typing in an input
      if (e.key === '/' && !isInput) {
        e.preventDefault()
        if (onSearchFocus) {
          onSearchFocus()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onSearchFocus, onEscape])
}
