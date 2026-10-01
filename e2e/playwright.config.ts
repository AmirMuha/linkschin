import { defineConfig, devices } from '@playwright/test'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const API_PORT = 8010
const API = `http://127.0.0.1:${API_PORT}`
const WEB = 'http://localhost:3000'
const STUB_PORT = 8910
const STUB = `http://127.0.0.1:${STUB_PORT}`
// __dirname, not import.meta.dirname: Node loads a .ts config as CJS unless the nearest
// package.json sets "type": "module", and import.meta then throws at load.
const HERE = __dirname
const REPO = join(HERE, '..')

// Every enabled scraper points at the stub. Two consequences worth stating:
//  1. Item links inside the recorded fixtures are absolute upstream URLs and clean_absolute_url
//     discards the base for those, so the stub also rewrites the fixture host on the way out.
//  2. Its CDN/media hosts are rewritten too, so validate_stream_url's HEAD resolves locally in
//     ~1ms instead of taking 7-8s against the real web and breaching the 10s search deadline.
const SOURCES = ['UPTVS', 'DOOSTIHAA', 'DOWNLOADHA', 'YASDL', 'POPMUSIC', 'NEX1MUSIC']
const sourceUrlEnv = Object.fromEntries(SOURCES.map((id) => [`LINKSCHIN_URL_${id}`, `${STUB}/${id.toLowerCase()}`]))

// Per-run SQLite, so no test reads another test's index.
const dbPath = join(mkdtempSync(join(tmpdir(), 'mf-e2e-')), 'index.db')

// cwd is load-bearing: the repo root carries stale duplicate modules and empty web/ and
// sources/ dirs, so only apps/api is a real entrypoint.
//
// Never reuse: something unrelated already answers on 8000 here, and silently adopting
// it would send every search to a different project's API.
const apiServer = {
  // Absolute: cwd is apps/api, whose .venv/ is the repo-root symlink. Relative breaks in a
  // linked git worktree where that symlink was never created.
  command: `${join(REPO, '.venv', 'bin', 'uvicorn')} main:app --port ${API_PORT} --host 127.0.0.1`,
  cwd: join(REPO, 'apps', 'api'),
  url: `${API}/health`,
  reuseExistingServer: false,
  env: { LINKSCHIN_DB: dbPath, ...sourceUrlEnv },
}

// The live project is config-level, not project-level: `webServer` is not a project option,
// so setting it under a project is silently ignored. The same three servers cover both cases —
// the live tests reach the real portals because the *API* then resolves the upstream hosts
// itself, and the browser never talks to them directly.
const servers = [apiServer, {
  command: `node ${join(HERE, 'stub-upstream.mjs')}`,
  url: `${STUB}/healthz`,
  reuseExistingServer: false,
  // The stub has its own E2E_STUB_PORT default; without this it would listen on 8899
  // regardless of the STUB url above.
  env: { E2E_STUB_PORT: String(STUB_PORT) },
}, {
  command: 'pnpm dev',
  cwd: join(REPO, 'apps', 'web'),
  url: WEB,
  reuseExistingServer: !process.env.CI,
  env: { NEXT_PUBLIC_API_BASE: API },
}]

export default defineConfig({
  testDir: './specs',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  // A search that fans out to two sources with a CDN HEAD each must not trip the budget.
  timeout: 45_000,
  expect: { timeout: 10_000 },
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : [['list'], ['html', { open: 'never' }]],

  use: {
    baseURL: WEB,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    // So audio.play() resolves without depending on a user gesture.
    launchOptions: { args: ['--autoplay-policy=no-user-gesture-required'] },
  },

  projects: [
    {
      name: 'hermetic-chromium',
      use: { ...devices['Desktop Chrome'], permissions: ['clipboard-read', 'clipboard-write'] },
    },
    {
      // Firefox has a different clipboard permission model, so the copy specs skip it.
      name: 'hermetic-firefox',
      use: devices['Desktop Firefox'],
      testIgnore: /clipboard\.spec\.ts/,
    },
    {
      name: 'mobile-375',
      use: { ...devices['Desktop Chrome'], viewport: { width: 375, height: 667 }, permissions: ['clipboard-read', 'clipboard-write'] },
    },
    {
      // Opt-in only: real upstream portals, best-effort by construction.
      name: 'live',
      grep: /@live/,
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: servers,
})
