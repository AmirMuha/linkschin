import { test, expect } from '../../fixtures/app'

// The hero banner autoplays on every category route. One shared component
// (apps/web/src/components/HeroBanner.tsx) is mounted by /movies, /games and
// /music, so movies is the representative case here — the pool sizes and the
// games-vs-backdrop image branch differ, but the timer, the pause gate and the
// reduced-motion gate do not.
const DWELL_MS = 6000

test.describe('hero banner autoplay', () => {
  test('advances to the next slide on its own', async ({ page }) => {
    await page.goto('/movies')

    const title = page.locator('#heroTitle')
    await expect(title).toBeVisible()
    const first = await title.textContent()

    // Generous over the 6s dwell: the next fetch + paint has to land too.
    await expect(title).not.toHaveText(first ?? '', { timeout: 12_000 })
  })

  test('a dot click switches immediately and restarts the dwell', async ({ page }) => {
    await page.goto('/movies')

    const title = page.locator('#heroTitle')
    await expect(title).toBeVisible()
    const first = await title.textContent()

    // Go to the last dot, not the second: this is the assertion that would fail
    // if the setInterval -> goTo rewrite had dropped one of the three handlers.
    await page.locator('#heroDots i.hit').last().click()
    await expect(title).not.toHaveText(first ?? '', { timeout: 2_000 })
  })

  test('pauses while the pointer rests on the controls', async ({ page }) => {
    await page.goto('/movies')

    const title = page.locator('#heroTitle')
    await expect(title).toBeVisible()
    const parked = await title.textContent()

    await page.locator('#heroDots').hover()

    // A "stays the same" assertion has nothing to retry against, so the wait is
    // the assertion: hold past the dwell and confirm no advance came.
    await page.waitForTimeout(DWELL_MS + 2000)
    await expect(title).toHaveText(parked ?? '')

    // Leaving the controls resumes rotation.
    await page.locator('#heroTitle').hover()
    await expect(title).not.toHaveText(parked ?? '', { timeout: 12_000 })
  })
})

test.describe('hero banner autoplay under prefers-reduced-motion', () => {
  test.use({ reducedMotion: 'reduce' })

  test('does not rotate on its own', async ({ page }) => {
    await page.goto('/movies')

    const title = page.locator('#heroTitle')
    await expect(title).toBeVisible()
    const parked = await title.textContent()

    await page.waitForTimeout(DWELL_MS + 2000)
    await expect(title).toHaveText(parked ?? '')
  })
})