import { test, expect, type Page } from '@playwright/test'

async function login(page: Page): Promise<void> {
  await page.goto('/')
  const loginButton = page.getByRole('button', { name: 'Login as dev@local.dev' })
  await expect(loginButton).toBeVisible()
  await loginButton.click()
  const profileButton = page.getByRole('button', { name: 'Profile' })
  await expect(profileButton).toBeVisible()
  await profileButton.click()
  await expect(page.getByRole('button', { name: 'Add entry' })).toBeVisible()
}

async function clearAllEntries(page: Page): Promise<void> {
  const deleteButtons = page.getByRole('button', { name: 'Delete entry' })
  let count = await deleteButtons.count()
  while (count > 0) {
    await deleteButtons.first().click()
    count = await deleteButtons.count()
  }
  await page.getByRole('button', { name: 'Save' }).click()
  await page.waitForLoadState('networkidle')
}

test.beforeEach(async ({ page }) => {
  await login(page)
  await clearAllEntries(page)
})

test('empty state shows no entries and an Add entry button', async ({ page }) => {
  await expect(page.getByRole('button', { name: 'Add entry' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Delete entry' })).toHaveCount(0)
})

test('add and save an entry persists after round-trip', async ({ page }) => {
  await page.getByRole('button', { name: 'Add entry' }).click()

  const tagInput = page.getByPlaceholder('tag').last()
  await tagInput.fill('hobbies')

  const textarea = page.locator('textarea').last()
  await textarea.fill('reading and hiking')

  await page.getByRole('button', { name: 'Save' }).click()
  await page.waitForLoadState('networkidle')

  await expect(page.locator('textarea').last()).toHaveValue('reading and hiking')
})

test('delete an entry and save removes it', async ({ page }) => {
  await page.getByRole('button', { name: 'Add entry' }).click()

  const tagInput = page.getByPlaceholder('tag').last()
  await tagInput.fill('hobbies')

  const textarea = page.locator('textarea').last()
  await textarea.fill('to be deleted')

  await page.getByRole('button', { name: 'Save' }).click()
  await page.waitForLoadState('networkidle')

  await expect(page.locator('textarea').last()).toHaveValue('to be deleted')

  await page.getByRole('button', { name: 'Delete entry' }).last().click()

  await page.getByRole('button', { name: 'Save' }).click()
  await page.waitForLoadState('networkidle')

  await expect(page.getByRole('button', { name: 'Delete entry' })).toHaveCount(0)
})

test('tag autocomplete shows known tags as suggestions', async ({ page }) => {
  await page.getByRole('button', { name: 'Add entry' }).click()

  const tagInput = page.getByPlaceholder('tag').last()
  await tagInput.focus()

  await expect(page.getByRole('button', { name: 'food_restrictions' })).toBeVisible()
})
