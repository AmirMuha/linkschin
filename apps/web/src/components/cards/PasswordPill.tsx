'use client'

import React, { useState } from 'react'
import { KeyRound, Copy, Check } from 'lucide-react'
import { copyToClipboard } from '@/lib/clipboard'
import { useToast } from '@/components/ui/ToastNotification'
import { TechnicalText } from '@/components/ui/TechnicalText'

interface PasswordPillProps {
  password: string
}

export function PasswordPill({ password }: PasswordPillProps) {
  const { showToast } = useToast()
  const [copied, setCopied] = useState(false)

  if (!password) return null

  async function handleCopy() {
    const ok = await copyToClipboard(password)
    if (ok) {
      setCopied(true)
      showToast('رمز فایل کپی شد', 'success')
      setTimeout(() => setCopied(false), 2000)
    } else {
      showToast('خطا در کپی رمز فایل', 'error')
    }
  }

  return (
    <div className="flex items-center justify-between gap-2 px-3 py-1.5 rounded-xl bg-zinc-800/80 border border-zinc-700/80 text-xs">
      <div className="flex items-center gap-1.5 text-zinc-400">
        <KeyRound className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
        <span className="text-zinc-400">رمز فایل:</span>
        <TechnicalText className="text-cyan-300 font-medium select-all">
          {password}
        </TechnicalText>
      </div>

      <button
        type="button"
        onClick={handleCopy}
        title="کپی رمز فایل"
        aria-label="کپی رمز فایل"
        className="p-1 rounded-lg hover:bg-zinc-700 text-zinc-400 hover:text-zinc-100 transition-colors"
      >
        {copied ? (
          <Check className="w-3.5 h-3.5 text-emerald-400" />
        ) : (
          <Copy className="w-3.5 h-3.5" />
        )}
      </button>
    </div>
  )
}
