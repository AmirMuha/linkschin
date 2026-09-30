import { test, expect } from '../../fixtures/app'

// 007 US2 — censorship badges and strict filtering.
//
// The recorded fixtures are deliberately sparse, and the spec's clarification is strict
// verification: a source that says nothing stays `unspecified`. uptvs carries no censorship
// marker at all (all 18 cards "نامشخص"); the five doostihaa items that got an item-page
// fetch read the fixture's `نسخه سانسور شده` tag and badge as "بازبینی شده" with every
// download row tagged "سانسور شده". The other five doostihaa cards were never enriched and
// stay "نامشخص" like the uptvs ones.
test.describe('007 US2 — censorship status visibility and filtering', () => {
  test('[007-US2-AC1][FR-004][FR-005] every card badges its censorship status', async ({ page, search }) => {
    await page.goto('/')
    await search('batman')
    const cards = page.getByRole('article')
    await expect(cards).toHaveCount(28)

    // A badge on every card — 23 unspecified, 5 read from the doostihaa item page.
    await expect(page.getByText('نامشخص', { exact: true })).toHaveCount(23)
    await expect(page.getByText('بازبینی شده', { exact: true })).toHaveCount(5)
    await expect(cards.filter({ hasText: 'Knightfall' }).first().getByText('بازبینی شده', { exact: true })).toBeVisible()
  })

  test('[007-US2-AC2][FR-006][FR-011] uncensored-only empties the grid without a new query', async ({ page, search, requests }) => {
    await page.goto('/')
    await search('batman')
    await expect(page.getByRole('article')).toHaveCount(28)

    const before = requests.filter((u) => u.includes('/api/search')).length
    await page.getByRole('button', { name: 'بدون سانسور' }).click()

    // Strict verification: nothing in these fixtures is verified uncensored, and every
    // unspecified title is excluded, so no card survives.
    await expect(page.getByRole('article')).toHaveCount(0)
    await expect(page.getByText('نتیجه‌ای با این فیلترها نیست')).toBeVisible()
    expect(requests.filter((u) => u.includes('/api/search')).length).toBe(before)
  })

  test('[007-US2-AC2][FR-006] censored-only keeps the enriched doostihaa cards', async ({ page, search }) => {
    await page.goto('/')
    await search('batman')
    await page.getByRole('button', { name: 'سانسور شده' }).click()

    // Only the five item pages carrying "نسخه سانسور شده" resolve; the 23 unspecified
    // cards are excluded rather than guessed into the bucket.
    await expect(page.getByRole('article')).toHaveCount(5)
    await expect(page.getByText('نامشخص', { exact: true })).toHaveCount(0)
    await expect(page.getByText('بازبینی شده', { exact: true })).toHaveCount(5)
  })

  test('[007-US2-AC3][FR-007] each surviving download row declares its censorship state', async ({ page, search }) => {
    await page.goto('/')
    await search('batman')

    const card = page.getByRole('article').filter({ hasText: 'Knightfall' }).first()
    // The fixture yields 1080p/720p/480p x dubbed/subbed; all six read the page-level tag.
    await expect(card.getByLabel('کپی لینک مستقیم')).toHaveCount(6)
    await expect(card.getByText('سانسور شده', { exact: true })).toHaveCount(6)
  })

  test('[007-US2-AC4][FR-006] unspecified items are the ones shown under all', async ({ page }) => {
    await page.goto('/?q=batman&censorship=uncensored')

    // The neutral "نامشخص" badge is the unspecified indicator, and those items appear only
    // when the filter is "All" — which is what the bare ?q=batman link is.
    await page.goto('/?q=batman')
    await expect(page.getByRole('article')).toHaveCount(28)
    await expect(page.getByText('نامشخص', { exact: true })).toHaveCount(23)
  })

  test('[007-US2-AC4][FR-006] the empty-filtered-results panel resets the filters in one click', async ({ page, search }) => {
    await page.goto('/')
    await search('batman')
    await page.getByRole('button', { name: 'بدون سانسور' }).click()
    await expect(page.getByRole('article')).toHaveCount(0)

    await page.getByRole('button', { name: 'حذف فیلترها' }).click()
    await expect(page.getByRole('article')).toHaveCount(28)
    expect(new URL(page.url()).searchParams.get('censorship')).toBeNull()
  })

  test('[007-US2-AC2][FR-012] a reload restores the censorship filter and replays the search', async ({ page }) => {
    await page.goto('/?q=batman&censorship=censored')

    await expect(page.getByRole('article')).toHaveCount(5)
    await expect(page.getByRole('textbox', { name: 'متن جستجو' })).toHaveValue('batman')
    await expect(page.getByRole('button', { name: 'سانسور شده' })).toHaveAttribute('aria-pressed', 'true')
    expect(new URL(page.url()).searchParams.get('censorship')).toBe('censored')
  })
})
