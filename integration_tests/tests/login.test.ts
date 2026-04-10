import { test, expect } from '@playwright/test'

test('dev login flow shows app message', async ({ page }) => {
  await page.goto('/')

  const loginButton = page.getByRole('button', { name: 'Login as dev@local.dev' })
  await expect(loginButton).toBeVisible()

  await loginButton.click()

  await expect(page.getByText('hello from chai-s-romashkoi')).toBeVisible()
})
