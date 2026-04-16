import { test, expect } from '@playwright/test'

test('dev login lands on the chat page and can navigate to profile', async ({ page }) => {
  await page.goto('/')

  const loginButton = page.getByRole('button', { name: 'Login' })
  await expect(loginButton).toBeVisible()

  await loginButton.click()

  const profileButton = page.getByRole('button', { name: 'Profile' })
  await expect(profileButton).toBeVisible()
  await profileButton.click()

  await expect(page.getByRole('button', { name: 'Add entry' })).toBeVisible()
})
