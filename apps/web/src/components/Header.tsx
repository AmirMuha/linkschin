'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import type { Category } from '@/types/media'
import { resolveNavPage, type NavPage } from '@/lib/nav'
import {
  Film,
  Gamepad2,
  Music,
  Heart,
  Server,
  Download,
  Sparkles,
  Menu,
  X,
} from 'lucide-react'

interface HeaderProps {
  category?: Category
  onCategoryChange?: (cat: Category) => void
  onOpenAi?: () => void
  activePage?: NavPage
  rightSlot?: React.ReactNode
}

export function Header({
  category,
  onOpenAi,
  activePage,
  rightSlot,
}: HeaderProps) {
  const [navOpen, setNavOpen] = useState(false)
  const pathname = usePathname()

  const current = activePage || resolveNavPage(pathname) || category

  return (
    <header className="hdr" data-od-id="site-header">
      <Link className="brand" href="/" aria-label="لینک‌چین، صفحه اصلی">
        <img
          src="/images/brand/logo.png"
          alt="لوگوی لینک‌چین"
          width={32}
          height={32}
        />
        <img
          className="brand-word"
          src="/images/brand/linkschin-wordmark.png"
          alt="لینک‌چین"
          height={40}
        />
      </Link>

      <nav
        className={`nav ${navOpen ? 'on' : ''}`}
        id="primary-nav"
        aria-label="ناوبری اصلی"
      >
        <Link
          href="/movies"
          data-page="movies"
          aria-current={current === 'movies' ? 'page' : undefined}
          onClick={() => setNavOpen(false)}
        >
          <Film className="w-4 h-4" />
          <span>فیلم و سریال</span>
        </Link>

        <Link
          href="/games"
          data-page="games"
          aria-current={current === 'games' ? 'page' : undefined}
          onClick={() => setNavOpen(false)}
        >
          <Gamepad2 className="w-4 h-4" />
          <span>بازی‌ها</span>
        </Link>

        <Link
          href="/music"
          data-page="music"
          aria-current={current === 'music' ? 'page' : undefined}
          onClick={() => setNavOpen(false)}
        >
          <Music className="w-4 h-4" />
          <span>موسیقی</span>
        </Link>

        <Link
          href="/favorites"
          data-page="favorites"
          aria-current={current === 'favorites' ? 'page' : undefined}
          onClick={() => setNavOpen(false)}
        >
          <Heart className="w-4 h-4" />
          <span>علاقه‌مندی‌ها</span>
        </Link>

        <Link
          href="/sources"
          data-page="sources"
          aria-current={current === 'sources' ? 'page' : undefined}
          onClick={() => setNavOpen(false)}
        >
          <Server className="w-4 h-4" />
          <span>منابع</span>
        </Link>

        <Link
          href="/youtube-to-mp3"
          data-page="mp3"
          aria-current={current === 'mp3' ? 'page' : undefined}
          onClick={() => setNavOpen(false)}
        >
          <Download className="w-4 h-4" />
          <span dir="ltr">MP3</span>
        </Link>
      </nav>

      <div className="hdr-right">
        {rightSlot}
        {/* ponytail: hide askAi button; restore when ready */}
        <button
          className="burger"
          type="button"
          aria-label="منو"
          aria-expanded={navOpen}
          onClick={() => setNavOpen((prev) => !prev)}
        >
          {navOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>
    </header>
  )
}
