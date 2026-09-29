// Hermetic stand-in for the six upstream portals, for the Playwright e2e suite.
//
// Serves the real recorded fixtures from apps/api/tests/fixtures/ (no new HTML), with
// the upstream host rewritten to this server so extract_links()'s second-hop page_url
// fetch stays local. Media URLs in those fixtures point at real CDNs on purpose:
// the app must hand them to the browser unproxied (Constitution III), and Playwright's
// page.route intercepts them before the browser ever leaves the machine.
//
// Control surface. The stub is per-source by path prefix, so a test selects a source
// with MOVIE_FETCHER_ENABLE_<ID>=false rather than a URL switch.
//
//   ?fail=1  on the source's base URL -> 503 for that source, producing the
//            partial-failure warning pill while the other enabled sources still answer.
//   q=__empty__         -> search page with every result anchor stripped (empty state)
//   q=__missing_parts__ -> item page with two archive-part anchors removed
import { createServer } from 'node:http'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const HERE = dirname(fileURLToPath(import.meta.url))
const FIXTURES = join(HERE, '..', 'apps', 'api', 'tests', 'fixtures')
const PORT = Number(process.env.E2E_STUB_PORT ?? 8899)
const SELF = `http://127.0.0.1:${PORT}`

// All six enabled sources are pointed at SELF via MOVIE_FETCHER_URL_<ID>, so the stub
// cannot tell them apart by host. Each gets its own path prefix instead.
const SOURCES = {
  uptvs: { prefix: '/uptvs', host: 'https://www.uptvs.com' },
  doostihaa: { prefix: '/doostihaa', host: 'https://www.doostihaa.com' },
  downloadha: { prefix: '/downloadha', host: 'https://www.downloadha.com' },
  yasdl: { prefix: '/yasdl', host: 'https://www.yasdl.com' },
  popmusic: { prefix: '/popmusic', host: 'https://pop-music.ir' },
  nex1music: { prefix: '/nex1music', host: 'https://nex1music.com' },
}

// Media/CDN hosts the recorded fixtures point at. validate_stream_url() HEADs every
// movie stream_url against the real web, which takes 7-8s and breaches the 10s global
// search deadline -- and leaks live traffic out of a suite that must be hermetic. These
// are rewritten to SELF + /cdn/<slug>/... so the HEAD resolves here in ~1ms.
// Deliberately excludes the six item hosts (pop-music.ir, nex1music.com, ...): rewriting
// those would point extract_links at the media branch and return an empty body.
// The URLs the browser renders are never rewritten (see send), so the no-relay oracle
// still asserts against the real upstream host.
const CDN_HOSTS = [
  'https://cdn.uptvs.com',
  'https://hub.irdanlod.ir',
  'https://dl.yasdl.com',
  'https://dl5.dlhas.ir',
  'https://dl.downloadha.com',
]

const reads = new Map()

function fixture(id, { empty = false, missingParts = false } = {}) {
  let html = readFileSync(join(FIXTURES, `${id}.html`), 'utf8')
  if (empty) html = html.replace(/<a[^>]+href=["'][^"']+["'][^>]*>/g, '<a>')
  if (missingParts) {
    // Drop two archive-part anchors so the real parser sets has_missing_parts.
    const re = /<a\s+[^>]*href=["'][^"']+\.(?:rar|zip|7z|bin|iso)(?:\?[^"']*)?["'][^>]*>.*?<\/a>/gis
    const kept = []
    let seen = 0
    let m
    while ((m = re.exec(html)) !== null) {
      kept.push(m[0])
      if (++seen >= 3) break
    }
    if (seen) html = html.replace(re, () => '') + kept.join('')
  }
  return html
}

function resolve(url) {
  const u = new URL(url, SELF)
  const entry = Object.entries(SOURCES).find(([, s]) => u.pathname.startsWith(s.prefix))
  if (!entry) return null
  const [id, src] = entry
  const isSearch = u.pathname === `${src.prefix}/` || u.pathname === src.prefix || u.searchParams.has('s')
  const isNex1 = id === 'nex1music' && /^\/nex1music\/search\//.test(u.pathname)
  const page = isNex1 || isSearch ? 'search' : 'item'
  return { id, src, page, params: u.searchParams }
}

const server = createServer((req, res) => {
  const url = req.url ?? '/'
  // Readiness probe for Playwright's webServer. It must resolve to a 2xx: every other
  // path here 404s for an unknown source prefix, and a 404 fails the readiness poll.
  if (url === '/healthz') {
    res.writeHead(200, { 'content-type': 'text/plain' }).end('ok')
    return
  }
  if (url === '/__requests') {
    res.writeHead(200, { 'content-type': 'application/json' })
    res.end(JSON.stringify([...reads].map(([k, v]) => ({ url: k, count: v }))))
    return
  }
  if (url === '/__reset') {
    reads.clear()
    res.writeHead(204).end()
    return
  }
  // Media endpoints the browser requests, and the CDN stand-in that validate_stream_url
  // HEADs (sources/base.py:105). is_directly_playable() checks status<400 + audio|video
  // MIME + an ACAO header, so the headers are the point; the body just has to match
  // content-length or httpx raises IncompleteRead and the caller swallows it.
  if (url.startsWith('/cdn/') || /\.(mp3|mp4)$/.test(url.split('?')[0])) {
    res.writeHead(200, {
      'content-type': url.includes('.mp3') ? 'audio/mpeg' : 'video/mp4',
      'access-control-allow-origin': '*',
      'content-length': '1',
    })
    res.end(Buffer.alloc(1))
    return
  }

  const hit = resolve(url)
  if (!hit) {
    res.writeHead(404, { 'content-type': 'text/plain' }).end('no such source')
    return
  }
  reads.set(url, (reads.get(url) ?? 0) + 1)

  if (hit.params.get('fail')) {
    res.writeHead(503, { 'content-type': 'text/plain' }).end('upstream down')
    return
  }
  if (hit.params.get('delay')) {
    const ms = Math.min(Number(hit.params.get('delay')) || 0, 10000)
    setTimeout(() => send(res, hit, {}), ms)
    return
  }

  // Control params may ride on the search URL but must not travel to the item page,
  // or a search-driven mode would silently apply to the follow-up fetch as well.
  const q = hit.params.get('q') ?? ''
  const opts = {
    empty: q.includes('__empty__'),
    missingParts: q.includes('__missing_parts__'),
  }
  send(res, hit, opts)
})

function send(res, hit, opts) {
  let html = fixture(`${hit.id}_${hit.page}`, opts)
  // CDN/media URLs go to the stub so the server-side HEAD is local and instant.
  for (const host of CDN_HOSTS) html = html.split(host).join(SELF + '/cdn/' + host.replace(/^https?:\/\//, '').replace(/[./]/g, '-'))
  // The item host goes to SELF *including the source prefix*, so the absolute item links
  // the parser picks up resolve back to this server rather than to /contents/... (404).
  // Done last, so the CDN rewrite cannot be re-pointed at the item host.
  html = html.split(hit.src.host).join(SELF + hit.src.prefix)
  res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' })
  res.end(html)
}

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[stub-upstream] listening on ${SELF} for ${Object.keys(SOURCES).join(', ')}`)
})
