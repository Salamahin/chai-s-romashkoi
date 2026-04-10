import { test, expect } from '@playwright/test'

test('dev login flow loads the profile page', async ({ page }) => {
  await page.goto('/')

  const loginButton = page.getByRole('button', { name: 'Login as dev@local.dev' })
  await expect(loginButton).toBeVisible()

  await loginButton.click()

  await expect(page.getByRole('button', { name: 'Add entry' })).toBeVisible()
})
