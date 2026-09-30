import { test, expect } from '../../fixtures/app'

// 007 US1 — filtering sources by access tier.
//
// Counts are pinned to the recorded fixtures for "batman": 18 uptvs cards (tier `free`)
// + 10 doostihaa cards (tier `freemium`) = 28. No fixture declares a `premium` source and
// no fixture carries a VIP link, so `is_premium` is false on every variant: the
// "premium only" chip legitimately leaves the freemium cards standing. The pruning of
// individual VIP rows is proven by apps/web/src/lib/filters.test.ts, not by fixtures.
test.describe('007 US1 — access tier filtering', () => {
  test('[007-US1-AC1][FR-002][FR-011] free-only keeps freemium cards and refines client-side', async ({ page, search, requests }) => {
    await page.goto('/')
    await search('batman')
    await expect(page.getByRole('article')).toHaveCount(28)

    const before = requests.filter((u) => u.includes('/api/search')).length
    await page.getByRole('button', { name: 'فقط رایگان' }).click()

    // Every source behind these fixtures is free or freemium, so nothing is removed, and no
    // download row is VIP-tagged, so no row is pruned either.
    await expect(page.getByRole('article')).toHaveCount(28)
    await expect(page.getByText('VIP', { exact: true })).toHaveCount(0)

    // FR-011: the grid was refined from the already-fetched items — no second backend query.
    expect(requests.filter((u) => u.includes('/api/search')).length).toBe(before)
  })

  test('[007-US1-AC2][FR-002] premium-only keeps freemium sources and drops the free ones', async ({ page, search }) => {
    await page.goto('/')
    await search('batman')
    await page.getByRole('button', { name: 'فقط اشتراکی / VIP' }).click()

    // The fixtures ship no purely-premium source, so what survives is the freemium one.
    await expect(page.getByRole('article')).toHaveCount(10)
    await expect(page.getByText('ترکیبی', { exact: true })).toHaveCount(10)
    await expect(page.getByText('رایگان', { exact: true })).toHaveCount(0)

    // No fixture link is VIP-flagged, so the five enriched cards have no row left to show.
    await expect(page.getByText('هیچ لینکی با فیلترهای فعلی مطابقت ندارد.')).toHaveCount(5)
  })

  test('[007-US1-AC3][FR-001][FR-003] every card carries the access tier of its source', async ({ page, search }) => {
    await page.goto('/')
    await search('batman')
    const cards = page.getByRole('article')
    await expect(cards).toHaveCount(28)

    // One tier badge per card, and it names the tier the registry declares for that source.
    await expect(page.getByText(/^(رایگان|ترکیبی|VIP)$/)).toHaveCount(28)
    await expect(cards.filter({ hasText: 'سقوط شوالیه' }).first().getByText('رایگان', { exact: true })).toBeVisible()
    await expect(cards.filter({ hasText: 'Knightfall' }).first().getByText('ترکیبی', { exact: true })).toBeVisible()
  })

  test('[007-US1-AC2][FR-012] a reload restores the tier filter and replays the search', async ({ page }) => {
    await page.goto('/?q=batman&tier=free')

    await expect(page.getByRole('article')).toHaveCount(28)
    await expect(page.getByRole('textbox', { name: 'متن جستجو' })).toHaveValue('batman')
    await expect(page.getByRole('button', { name: 'فقط رایگان' })).toHaveAttribute('aria-pressed', 'true')
    expect(new URL(page.url()).searchParams.get('tier')).toBe('free')
  })
})
