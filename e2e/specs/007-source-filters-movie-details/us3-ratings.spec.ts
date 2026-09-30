import { test, expect } from '../../fixtures/app'

// 007 US3 — IMDb rating on the poster overlay.
//
// Pinned to the recorded fixtures: 25/28 "batman" cards carry an IMDb score (3 unrated:
// سیلو, باب اسفنجی, From) and 4 of them read exactly 7.9. The score is extracted from the
// upstream HTML only; nothing here calls a third-party rating service.
test.describe('007 US3 — imdb rating on movie cards', () => {
  test('[007-US3-AC1][FR-008][FR-009] a rated card shows the star badge and its score', async ({ page, search }) => {
    await page.goto('/')
    await search('batman')

    const card = page.getByRole('article').filter({ hasText: 'سقوط شوالیه' }).first()
    // The badge is a Star icon beside a monospace one-decimal score, on the poster overlay.
    await expect(card.getByText('7.9', { exact: true })).toBeVisible()
    await expect(card.locator('svg.fill-amber-400')).toBeVisible()

    // The score is on the overlay, not in the metadata block below the poster.
    const overlay = card.locator('div.relative').first()
    await expect(overlay.getByText('7.9', { exact: true })).toBeVisible()
  })

  test('[007-US3-AC1][FR-008] every rated fixture card surfaces its score', async ({ page, search }) => {
    await page.goto('/')
    await search('batman')
    await expect(page.getByRole('article')).toHaveCount(28)

    // 25 rated cards + 3 unrated placeholders = the badge is on all 28, none omitted.
    await expect(page.getByText('7.9', { exact: true })).toHaveCount(4)
    await expect(page.getByText('6.0', { exact: true })).toHaveCount(1)
    await expect(page.getByText('—', { exact: true })).toHaveCount(3)
  })

  test('[007-US3-AC2][FR-010] an unrated card shows the em-dash placeholder', async ({ page, search }) => {
    await page.goto('/')
    await search('batman')

    const card = page.getByRole('article').filter({ hasText: 'سیلو' }).first()
    await expect(card.getByText('—', { exact: true })).toBeVisible()
    // The star icon still renders: the placeholder must not shift the layout.
    await expect(card.locator('svg.fill-amber-400')).toBeVisible()
  })

  test('[007-US3-AC3][FR-009] the score badge keeps its size when the rating is missing', async ({ page, search }) => {
    await page.goto('/')
    await search('batman')

    const badge = page.getByRole('article').filter({ hasText: 'سقوط شوالیه' }).first().locator('svg.fill-amber-400').locator('..')
    const unrated = page.getByRole('article').filter({ hasText: 'سیلو' }).first().locator('svg.fill-amber-400').locator('..')
    const [ratedBox, unratedBox] = await Promise.all([badge.boundingBox(), unrated.boundingBox()])
    expect(ratedBox!.height).toBe(unratedBox!.height)
    expect(ratedBox!.width).toBe(unratedBox!.width)
  })

  test('[007-US3-AC3][FR-009] the badge stays inside the card at a 375px viewport', async ({ page, search }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/')
    await search('batman')

    const card = page.getByRole('article').filter({ hasText: 'سقوط شوالیه' }).first()
    const cardBox = await card.boundingBox()
    const scoreBox = await card.getByText('7.9', { exact: true }).boundingBox()
    expect(scoreBox!.x).toBeGreaterThanOrEqual(cardBox!.x)
    expect(scoreBox!.x + scoreBox!.width).toBeLessThanOrEqual(cardBox!.x + cardBox!.width)
  })
})
