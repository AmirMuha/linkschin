import { test, expect } from '../../fixtures/app'

// 001 US1 — search and download movies/series by format.
// Assertions are pinned to the recorded fixtures in apps/api/tests/fixtures/, so the
// expected values are what the real parsers actually extract, not guesses.
test.describe('001 US1 — movie search and format variants', () => {
  test('[001-US1-AC1][FR-001] presents matching items with title, year and format variants', async ({ page, search }) => {
    await page.goto('/')
    await page.getByRole('tab', { name: 'فیلم و سریال' }).click()
    await search('batman')

    const card = page.getByRole('article').filter({ hasText: 'سقوط شوالیه' }).first()
    await expect(card).toBeVisible()
    await expect(card).toContainText('2026')
    // Only the first few items get extract_links() enrichment, and this card's 2 variants
    // are the part this AC holds.
    await expect(card.getByLabel('کپی لینک مستقیم')).toHaveCount(2)
  })

  test('[001-US1-AC2][FR-002] segments links by resolution and audio/subtitle track', async ({ page, search }) => {
    await page.goto('/')
    await search('batman')

    const card = page.getByRole('article').filter({ hasText: 'سقوط شوالیه' }).first()
    // Fixture yields 1080p and 720p, both soft-subbed.
    await expect(card.getByText('1080p').first()).toBeVisible()
    await expect(card.getByText('720p').first()).toBeVisible()
    await expect(card.getByText('زیرنویس فارسی').first()).toBeVisible()
  })

  test('[001-US1-AC3][FR-003] download href is not proxied through the API', async ({ page, request, search }) => {
    await page.goto('/')
    await search('batman')

    const card = page.getByRole('article').filter({ hasText: 'سقوط شوالیه' }).first()
    const href = await card.locator('a[download]').first().getAttribute('href')
    // The hermetic stub rewrites CDN hosts server-side, so the served URL is the stub's.
    // What Constitution III forbids is relaying *through our own app* — so assert the
    // href never points at the FastAPI origin, rather than pinning a fixture-specific host.
    expect(href).toBeTruthy()
    expect(href).not.toMatch(/127\.0\.0\.1:8010|localhost:8000/)

    // And the underlying media is fetched straight from the CDN by the browser, not via /api.
    const { items } = await (await request.get('http://127.0.0.1:8010/api/search?q=batman&category=movies')).json()
    for (const item of items.filter((i: { stream_url?: string }) => i.stream_url)) {
      expect(item.stream_url).not.toContain('8010')
    }
  })

  test('[001-US5-AC1][FR-021][FR-012] the browser never leaves the machine', async ({ page, search, offMachine }) => {
    await page.goto('/')
    await search('batman')
    await expect(page.getByRole('article').first()).toBeVisible()
    // The hermetic contract, and the strongest form of the no-relay requirement:
    // poster, cover, font and media requests are all fulfilled locally.
    expect(offMachine()).toEqual([])
  })
})
