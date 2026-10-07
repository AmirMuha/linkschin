import { test as base, expect, type Request } from '@playwright/test'

// 1x1 transparent PNG: satisfies <img> without a network fetch.
const PIXEL = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
  'base64',
)

export const LOCAL = /^(?:localhost|127\.0\.0\.1)(?::\d+)?$/

type App = {
  /** Every request the browser issued, for the no-relay oracle. */
  requests: string[]
  /** Requests that left the machine, i.e. violated the hermetic contract. */
  offMachine: () => string[]
  /** Media URLs the browser actually fetched (proves the player, not the server, played it). */
  media: () => string[]
  search: (query: string) => Promise<void>
}

export const test = base.extend<App>({
  requests: async ({}, use) => {
    await use([] as string[])
  },
  offMachine: async ({ requests }, use) => {
    await use(() => requests.filter((u) => {
      try {
        return !LOCAL.test(new URL(u).hostname)
      } catch {
        return false
      }
    }))
  },
  media: async ({ requests }, use) => {
    await use(() => requests.filter((u) => /\.(mp3|mp4)(\?|$)/.test(u)))
  },
  search: async ({ page }, use) => {
    // Scoped by role, not getByLabel: the clear button's label is
    // "پاک کردن متن جستجو", which substring-matches and trips strict mode.
    await use(async (query: string) => {
      const input = page.getByRole('searchbox', { name: 'متن جستجو' })
      await input.fill(query)
      await input.press('Enter')
    })
  },

  page: async ({ page, requests }, use) => {
    page.on('request', (r: Request) => requests.push(r.url()))

    // Anything off-localhost is fulfilled locally. Poster and cover URLs in the recorded
    // fixtures point at real upstream hosts, so without this the "hermetic" suite would
    // silently make live requests and the run would depend on the internet.
    await page.route('**/*', async (route) => {
      const host = new URL(route.request().url()).hostname
      if (LOCAL.test(host)) return route.continue()
      return route.fulfill({
        status: 200,
        contentType: route.request().resourceType() === 'image' ? 'image/png' : 'text/plain',
        body: route.request().resourceType() === 'image' ? PIXEL : '',
      })
    })

    // recent_searches and player_volume both persist across tests and would leak
    // suggestions / a stale volume into the next test's assertions.
    await page.addInitScript(() => window.localStorage.clear())

    await use(page)
  },
})

export { expect }
