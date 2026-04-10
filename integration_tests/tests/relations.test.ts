import { test, expect, type Page } from '@playwright/test'

const BACKEND = 'http://localhost:8000'

async function seedReceivedRelation(peerEmail: string, label: string): Promise<string> {
  const res = await fetch(`${BACKEND}/test/seed-relation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ peer_email: peerEmail, label }),
  })
  const data = (await res.json()) as { relation_id: string }
  return data.relation_id
}

async function loginAndGoToProfile(page: Page): Promise<void> {
  await page.goto('/')
  const loginButton = page.getByRole('button', { name: 'Login as dev@local.dev' })
  await expect(loginButton).toBeVisible()
  await loginButton.click()
  const profileButton = page.getByRole('button', { name: /^Profile/ })
  await expect(profileButton).toBeVisible()
  await profileButton.click()
  await expect(page.getByRole('button', { name: 'Add entry' })).toBeVisible()
}

async function clearAllRelations(page: Page): Promise<void> {
  // Wait for RelationsPanel's initial load to complete before interacting
  await page.waitForLoadState('networkidle')
  // Reject any pending-received relations first
  let count = await page.getByRole('button', { name: 'Reject' }).count()
  while (count > 0) {
    await page.getByRole('button', { name: 'Reject' }).first().click()
    await page.getByText('Loading…').waitFor({ state: 'visible', timeout: 3000 }).catch(() => {})
    await page.getByText('Loading…').waitFor({ state: 'hidden', timeout: 10000 }).catch(() => {})
    count = await page.getByRole('button', { name: 'Reject' }).count()
  }
  // Delete any pending-sent and confirmed relations
  count = await page.getByRole('button', { name: 'Delete' }).count()
  while (count > 0) {
    await page.getByRole('button', { name: 'Delete' }).first().click()
    await page.getByText('Loading…').waitFor({ state: 'visible', timeout: 3000 }).catch(() => {})
    await page.getByText('Loading…').waitFor({ state: 'hidden', timeout: 10000 }).catch(() => {})
    count = await page.getByRole('button', { name: 'Delete' }).count()
  }
}

test.beforeEach(async ({ page }) => {
  await loginAndGoToProfile(page)
  await clearAllRelations(page)
})

test('relations panel is visible on the profile page', async ({ page }) => {
  await expect(page.getByRole('button', { name: 'Send' })).toBeVisible()
})

test('send a relation request creates a pending sent entry', async ({ page }) => {
  await page.locator('input[placeholder="Recipient email"]').fill('other@example.com')
  await page.locator('input[placeholder="Label"]').fill('friend')
  await page.getByRole('button', { name: 'Send' }).click()
  await page.waitForLoadState('networkidle')

  await expect(page.getByText('other@example.com')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Delete' })).toBeVisible()
})

test('delete a pending sent relation removes it', async ({ page }) => {
  await page.locator('input[placeholder="Recipient email"]').fill('other@example.com')
  await page.locator('input[placeholder="Label"]').fill('friend')
  await page.getByRole('button', { name: 'Send' }).click()
  await page.waitForLoadState('networkidle')

  await expect(page.getByText('other@example.com')).toBeVisible()

  await page.getByRole('button', { name: 'Delete' }).click()
  await page.waitForLoadState('networkidle')

  await expect(page.getByText('other@example.com')).not.toBeVisible()
})

test('label autocomplete shows known labels after one is used', async ({ page }) => {
  await page.locator('input[placeholder="Recipient email"]').fill('other@example.com')
  await page.locator('input[placeholder="Label"]').fill('colleague')
  await page.getByRole('button', { name: 'Send' }).click()
  await page.waitForLoadState('networkidle')

  // Wait for sendLabel to be cleared by Svelte re-render after loadData
  await expect(page.locator('input[placeholder="Label"]')).toHaveValue('')
  await page.locator('input[placeholder="Label"]').click()

  await expect(page.getByRole('button', { name: 'colleague' })).toBeVisible()
})

test('confirm a received relation moves it to confirmed', async ({ page }) => {
  await seedReceivedRelation('sender@example.com', 'friend')
  await page.reload()
  await page.waitForLoadState('networkidle')
  await page.getByRole('button', { name: /^Profile/ }).click()
  await page.waitForLoadState('networkidle')

  await expect(page.getByRole('button', { name: 'Confirm' })).toBeVisible()
  await page.getByRole('button', { name: 'Confirm' }).click()
  await page.waitForLoadState('networkidle')

  await expect(page.getByRole('button', { name: 'Confirm' })).not.toBeVisible()
  await expect(page.getByRole('button', { name: 'Reject' })).not.toBeVisible()
  await expect(page.getByText('sender@example.com')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Delete' })).toBeVisible()
})

test('reject a received relation removes it', async ({ page }) => {
  await seedReceivedRelation('sender@example.com', 'colleague')
  await page.reload()
  await page.waitForLoadState('networkidle')
  await page.getByRole('button', { name: /^Profile/ }).click()
  await page.waitForLoadState('networkidle')

  await expect(page.getByRole('button', { name: 'Reject' })).toBeVisible()
  await page.getByRole('button', { name: 'Reject' }).click()
  await page.waitForLoadState('networkidle')

  await expect(page.getByText('sender@example.com')).not.toBeVisible()
})

test('delete a confirmed relation removes it', async ({ page }) => {
  await seedReceivedRelation('sender@example.com', 'workmate')
  await page.reload()
  await page.waitForLoadState('networkidle')
  await page.getByRole('button', { name: /^Profile/ }).click()
  await page.waitForLoadState('networkidle')

  await page.getByRole('button', { name: 'Confirm' }).click()
  await page.waitForLoadState('networkidle')

  await expect(page.getByText('sender@example.com')).toBeVisible()
  await page.getByRole('button', { name: 'Delete' }).click()
  await page.waitForLoadState('networkidle')

  await expect(page.getByText('sender@example.com')).not.toBeVisible()
})

test('pending badge shows on home page when a received relation is pending', async ({ page }) => {
  await seedReceivedRelation('sender@example.com', 'friend')
  // Navigate back to home to trigger a fresh getHomeData call
  await page.goto('/')
  await page.waitForLoadState('networkidle')

  const profileButton = page.getByRole('button', { name: /^Profile/ })
  await expect(profileButton).toBeVisible()
  await expect(profileButton).toContainText('1')
})
