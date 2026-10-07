import { test, expect } from '../../fixtures/app'

// Bug 2 — switching tabs must start a fresh query. The previous term belonged to a
// different category, and re-running it fired a search from the pre-switch handleSearch
// closure, so the new tab silently searched the old category.
//
// Every /api/search is fulfilled locally, so this runs without the API: the assertion is
// about client state (the input clears, no request fires), not about what comes back.
test.describe('search-tab-bugs — tab switch resets the query', () => {
  test.beforeEach(async ({ page }) => {
    let n = 0
    await page.route('**/api/search*', (route) => {
      n += 1
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ query: 'batman', category: 'movies', items: [], warnings: [] }),
      })
    })
  })

  test('clears the search input and does not auto-search the previous term', async ({ page, search }) => {
    // `/` lands on /movies; the category switch is a header link to /games now.
    await page.goto('/')
    await search('batman')
    await expect(page.getByRole('searchbox', { name: 'متن جستجو' })).toHaveValue('batman')

    const before = await page.locator('body').evaluate(() => performance.getEntriesByType('resource')
      .filter((e) => e.name.includes('/api/search')).length)
    expect(before).toBeGreaterThan(0)

    // Scoped to the header: the footer carries a link with the same name.
    await page
      .getByRole('navigation', { name: 'ناوبری اصلی' })
      .getByRole('link', { name: 'بازی‌ها' })
      .click()

    await expect(page.getByRole('searchbox', { name: 'متن جستجو' })).toHaveValue('')
    // The stale term must not be re-issued against the new category.
    await expect.poll(async () => page.locator('body').evaluate(() => performance.getEntriesByType('resource')
      .filter((e) => e.name.includes('/api/search')).length)).toBe(before)
  })
})
