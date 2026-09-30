'use client'

import React from 'react'
import { LockKeyhole } from 'lucide-react'
import type { LinkAccess } from '@/types/media'

/**
 * Marks a link whose host answers with a login/interstitial page instead of the
 * file. Rendered instead of a plain download button so the user is not told to
 * click through to a page that will never deliver the media.
 */
export function AccessBadge({ access }: { access?: LinkAccess }) {
  if (access !== 'needs_login') return null

  return (
    <span
      className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-300 text-2xs font-medium shrink-0"
      title="این لینک مستقیم نیست و پس از باز کردن، صفحهٔ ورود به حساب نمایش داده می‌شود."
    >
      <LockKeyhole className="w-3 h-3 shrink-0" />
      <span className="whitespace-nowrap">نیازمند ورود</span>
    </span>
  )
}