import React from 'react'
import Link from 'next/link'

export function Footer() {
  return (
    <footer className="ftr" data-od-id="site-footer">
      <div className="wrap">
        <div className="ftr-grid">
          <div>
            <Link className="brand" href="/" aria-label="Linkschin home">
              <img
                src="/images/brand/logo-with-text.png"
                alt="Linkschin — Movies, Games, Music"
                width={180}
                height={180}
                style={{ height: 'auto', maxWidth: '180px' }}
              />
            </Link>
            <p style={{ marginTop: '16px' }}>
              A direct-link aggregator for Iranian movie, game and music portals.
              This server never stores, hosts, proxies or relays a single byte of media — every link resolves
              straight from your browser to the upstream CDN.
            </p>
          </div>
          <div>
            <h3>Discover</h3>
            <ul>
              <li>
                <a href="#movies">Movies</a>
              </li>
              <li>
                <a href="#games">Games</a>
              </li>
              <li>
                <a href="#music">Music</a>
              </li>
              <li>
                <a href="#watchlist">Watchlist</a>
              </li>
              <li>
                <Link href="/youtube-to-mp3">YouTube → MP3</Link>
              </li>
            </ul>
          </div>
          <div>
            <h3>Legal &amp; info</h3>
            <ul>
              <li>
                <Link href="/sources">Source registry</Link>
              </li>
              <li>
                <Link href="/sources#suggest">Suggest a source</Link>
              </li>
              <li>
                <a href="#faq">FAQ</a>
              </li>
              <li>
                <Link href="/sources#legal">Content policy</Link>
              </li>
            </ul>
          </div>
        </div>
        <div className="ftr-base">
          <span>© 2026 Linkschin · direct-link aggregator</span>
          <span>This site stores no media. All catalogue metadata is resolved upstream.</span>
        </div>
      </div>
    </footer>
  )
}
