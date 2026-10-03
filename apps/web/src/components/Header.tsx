'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import type { Category } from '@/types/media'
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
  /** No 'home': the brand logo owns that destination, so nothing marks it current.
   *  Home's own Movies/Games/Music tabs are tracked by `category` instead. */
  activePage?: 'movies' | 'games' | 'music' | 'favorites' | 'sources' | 'mp3'
  rightSlot?: React.ReactNode
}

export function Header({
  category = 'movies',
  onCategoryChange,
  onOpenAi,
  activePage,
  rightSlot,
}: HeaderProps) {
  const [navOpen, setNavOpen] = useState(false)

  function handleNavClick(cat: Category) {
    onCategoryChange?.(cat)
    setNavOpen(false)
  }

  return (
    <header className="hdr" data-od-id="site-header">
      <Link className="brand" href="/" aria-label="لینک‌چین، صفحه اصلی">
        <img
          src="/images/brand/logo.png"
          alt="لوگوی لینک‌چین"
          width={32}
          height={32}
        />
        {/* Brand name stays Latin; `dir="ltr"` keeps it and its letter-spacing
            from being reordered inside the RTL shell. */}
        <span className="brand-word" dir="ltr">Linkschin</span>
      </Link>

      <nav
        className={`nav ${navOpen ? 'on' : ''}`}
        id="primary-nav"
        aria-label="ناوبری اصلی"
      >
        {/* No Home entry: the brand logo already links to `/`, so a tab for it
            would be a duplicate control for the same destination. */}
        {onCategoryChange ? (
          <>
            <button
              type="button"
              data-page="movies"
              aria-current={category === 'movies' ? 'page' : undefined}
              onClick={() => handleNavClick('movies')}
            >
              <Film className="w-4 h-4" />
              <span>فیلم و سریال</span>
            </button>
            <button
              type="button"
              data-page="games"
              aria-current={category === 'games' ? 'page' : undefined}
              onClick={() => handleNavClick('games')}
            >
              <Gamepad2 className="w-4 h-4" />
              <span>بازی‌ها</span>
            </button>
            <button
              type="button"
              data-page="music"
              aria-current={category === 'music' ? 'page' : undefined}
              onClick={() => handleNavClick('music')}
            >
              <Music className="w-4 h-4" />
              <span>موسیقی</span>
            </button>
          </>
        ) : (
          <>
            {/* These render on /sources and /youtube-to-mp3, where the home page's
                category is client state, not an anchor. `?cat=` is what page.tsx
                reads on mount, so it actually switches the tab; the old `/#movies`
                was a dead fragment that left home on Movies. */}
            <Link
              href="/?cat=movies"
              data-page="movies"
              aria-current={activePage === 'movies' ? 'page' : undefined}
              onClick={() => setNavOpen(false)}
            >
              <Film className="w-4 h-4" />
              <span>فیلم و سریال</span>
            </Link>
            <Link
              href="/?cat=games"
              data-page="games"
              aria-current={activePage === 'games' ? 'page' : undefined}
              onClick={() => setNavOpen(false)}
            >
              <Gamepad2 className="w-4 h-4" />
              <span>بازی‌ها</span>
            </Link>
            <Link
              href="/?cat=music"
              data-page="music"
              aria-current={activePage === 'music' ? 'page' : undefined}
              onClick={() => setNavOpen(false)}
            >
              <Music className="w-4 h-4" />
              <span>موسیقی</span>
            </Link>
          </>
        )}

        <Link
          href="/favorites"
          data-page="favorites"
          aria-current={activePage === 'favorites' ? 'page' : undefined}
          onClick={() => setNavOpen(false)}
        >
          <Heart className="w-4 h-4" />
          <span>علاقه‌مندی‌ها</span>
        </Link>

        <Link
          href="/sources"
          data-page="sources"
          aria-current={activePage === 'sources' ? 'page' : undefined}
          onClick={() => setNavOpen(false)}
        >
          <Server className="w-4 h-4" />
          <span>منابع</span>
        </Link>

        <Link
          href="/youtube-to-mp3"
          data-page="mp3"
          aria-current={activePage === 'mp3' ? 'page' : undefined}
          onClick={() => setNavOpen(false)}
        >
          <Download className="w-4 h-4" />
          <span dir="ltr">MP3</span>
        </Link>
      </nav>

      <div className="hdr-right">
        {rightSlot}
        {onOpenAi && (
          <button
            className="btn btn-ghost btn-sm"
            type="button"
            id="askAi"
            onClick={onOpenAi}
          >
            <Sparkles className="w-4 h-4" />
            <span>پرسش از هوش مصنوعی</span>
          </button>
        )}
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
