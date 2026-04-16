import { test, expect, type Page } from '@playwright/test'
import { E2E_USER } from '../test-constants'

const BACKEND = 'http://localhost:8000'

async function clearLog(): Promise<void> {
  await fetch(`${BACKEND}/test/clear-log`, { method: 'POST' })
}

async function loginToChat(page: Page): Promise<void> {
  await page.goto('/')
  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page.getByRole('button', { name: 'Send' })).toBeVisible()
  await page.waitForLoadState('networkidle')
}

async function sendMessage(page: Page, text: string): Promise<void> {
  await page.locator('textarea').first().fill(text)
  await page.getByRole('button', { name: 'Send' }).click()
  await page.waitForLoadState('networkidle')
}

test.beforeEach(async ({ page }) => {
  await clearLog()
  await loginToChat(page)
})

test('chat interface is visible after login', async ({ page }) => {
  await expect(page.getByRole('button', { name: /^Profile/ })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Send' })).toBeVisible()
  await expect(page.locator('textarea').first()).toBeVisible()
})

test('no HTTP error banner appears after initial load', async ({ page }) => {
  // If the initial GET /log call fails (e.g. returns 403 or 404) ChatPage renders
  // a red error banner with the HTTP status. Assert it is absent.
  await expect(page.getByText(/^HTTP \d{3}$/)).not.toBeVisible()
})

test('GET /log is called with correct path after login', async ({ page }) => {
  // Regression: Lambda Function URLs have a trailing slash; concatenating
  // it with "/log" produced "//log" which AWS rejects with 403.
  // Re-login from scratch so we can capture the initial request.
  await page.evaluate(() => sessionStorage.clear())

  const logUrls: string[] = []
  page.on('request', (req) => {
    if (req.method() === 'GET' && /^https?:\/\/localhost:8000\/.*log/.test(req.url())) {
      logUrls.push(req.url())
    }
  })

  await page.goto('/')
  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page.getByRole('button', { name: 'Send' })).toBeVisible()
  await page.waitForLoadState('networkidle')

  expect(logUrls.length).toBeGreaterThan(0)
  for (const url of logUrls) {
    expect(url).not.toMatch(/\/\/log/)
  }
})

test('403 on initial log fetch shows an error banner', async ({ page }) => {
  // Re-login from scratch with the intercept in place so it fires on the
  // initial ChatPage mount request.
  // Scope the pattern to the backend origin only — a broad "**/log*" also
  // matches Vite module requests like /src/lib/log_service.ts and breaks SPA loading.
  await page.evaluate(() => sessionStorage.clear())

  await page.route('http://localhost:8000/log*', (route) => {
    if (route.request().method() === 'GET') {
      route.fulfill({ status: 403, contentType: 'application/json', body: JSON.stringify({ error: 'forbidden' }) })
    } else {
      route.continue()
    }
  })

  await page.goto('/')
  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page.getByRole('button', { name: 'Send' })).toBeVisible()
  await page.waitForLoadState('networkidle')

  await expect(page.getByText('HTTP 403')).toBeVisible()
})

test('send a message and it appears in the chat', async ({ page }) => {
  await sendMessage(page, 'Hello from test')
  await expect(page.getByText('Hello from test')).toBeVisible()
})

test('message appears immediately in pending state before server responds', async ({ page }) => {
  await page.locator('textarea').first().fill('Optimistic message')
  await page.getByRole('button', { name: 'Send' }).click()
  // Should appear immediately without waiting for network
  await expect(page.getByText('Optimistic message')).toBeVisible()
})

test('sent message shows saved delivery indicator after server confirms', async ({ page }) => {
  await sendMessage(page, 'Delivered message')
  // After networkidle the message should have been confirmed by the server
  await expect(page.getByText('Delivered message')).toBeVisible()
})

test('input is cleared after sending', async ({ page }) => {
  await page.locator('textarea').first().fill('Some text')
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(page.locator('textarea').first()).toHaveValue('')
})

test('send multiple messages, all appear in order', async ({ page }) => {
  await sendMessage(page, 'First message')
  await sendMessage(page, 'Second message')
  await sendMessage(page, 'Third message')

  const items = page.getByText(/First message|Second message|Third message/)
  await expect(items.first()).toContainText('First message')
})

test('edit a message updates its text', async ({ page }) => {
  await sendMessage(page, 'Original text')

  await page.getByText('Original text').hover()
  await page.getByRole('button', { name: 'Edit' }).click()

  // Edit textarea renders inside the message list, before the input bar in DOM order
  await page.locator('textarea').first().fill('Edited text')
  await page.getByRole('button', { name: 'Save' }).click()
  await page.waitForLoadState('networkidle')

  await expect(page.getByText('Edited text')).toBeVisible()
  await expect(page.getByText('Original text')).not.toBeVisible()
})

test('cancel edit restores original text', async ({ page }) => {
  await sendMessage(page, 'Keep this text')

  await page.getByText('Keep this text').hover()
  await page.getByRole('button', { name: 'Edit' }).click()

  await page.locator('textarea').first().fill('Discarded change')
  await page.getByRole('button', { name: 'Cancel' }).click()

  await expect(page.getByText('Keep this text')).toBeVisible()
  await expect(page.getByText('Discarded change')).not.toBeVisible()
})

test('delete a message removes it from the chat', async ({ page }) => {
  await sendMessage(page, 'To be deleted')

  await page.getByText('To be deleted').hover()
  await page.getByRole('button', { name: 'Delete' }).click()
  await page.waitForLoadState('networkidle')

  await expect(page.getByText('To be deleted')).not.toBeVisible()
})

test('edited message shows edited label', async ({ page }) => {
  await sendMessage(page, 'Will be edited')

  await page.getByText('Will be edited').hover()
  await page.getByRole('button', { name: 'Edit' }).click()
  await page.locator('textarea').first().fill('Now edited')
  await page.getByRole('button', { name: 'Save' }).click()
  await page.waitForLoadState('networkidle')

  // "edited" label is a standalone span, use exact match to avoid matching message text
  await expect(page.getByText('edited', { exact: true })).toBeVisible()
})

test('profile button navigates to profile page', async ({ page }) => {
  await page.getByRole('button', { name: /^Profile/ }).click()
  await expect(page.getByRole('button', { name: 'Add entry' })).toBeVisible()
})

test('back from profile returns to chat', async ({ page }) => {
  await page.getByRole('button', { name: /^Profile/ }).click()
  await expect(page.getByRole('button', { name: 'Add entry' })).toBeVisible()

  await page.getByRole('button', { name: /back/i }).click()
  await expect(page.getByRole('button', { name: 'Send' })).toBeVisible()
})

test('send button is disabled when input is empty', async ({ page }) => {
  await expect(page.getByRole('button', { name: 'Send' })).toBeDisabled()
  await page.locator('textarea').first().fill('something')
  await expect(page.getByRole('button', { name: 'Send' })).toBeEnabled()
})

test('ctrl+enter sends the message', async ({ page }) => {
  await page.locator('textarea').first().fill('Sent via keyboard')
  await page.locator('textarea').first().press('Control+Enter')
  await expect(page.getByText('Sent via keyboard')).toBeVisible()
  await expect(page.locator('textarea').first()).toHaveValue('')
})

test('messages persist across page reload', async ({ page }) => {
  await sendMessage(page, 'Persistent message')

  await page.reload()
  await page.waitForLoadState('networkidle')

  await expect(page.getByText('Persistent message')).toBeVisible()
})

test('edit and delete buttons only appear for saved messages on hover', async ({ page }) => {
  await sendMessage(page, 'Hover test message')

  // Buttons hidden before hover
  await expect(page.getByRole('button', { name: 'Edit' })).not.toBeVisible()
  await expect(page.getByRole('button', { name: 'Delete' })).not.toBeVisible()

  // Buttons visible after hover
  await page.getByText('Hover test message').hover()
  await expect(page.getByRole('button', { name: 'Edit' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Delete' })).toBeVisible()
})

test('failed send shows failed state and retry delivers the message', async ({ page }) => {
  // Intercept POST /log to simulate a server error
  await page.route('**/log', (route) => {
    if (route.request().method() === 'POST') {
      route.fulfill({ status: 500, body: JSON.stringify({ error: 'server error' }) })
    } else {
      route.continue()
    }
  })

  await page.locator('textarea').first().fill('Message that will fail')
  await page.getByRole('button', { name: 'Send' }).click()

  await expect(page.getByText('Message that will fail')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Retry' })).toBeVisible()

  // Allow the retry to reach the server
  await page.unroute('**/log')

  await page.getByRole('button', { name: 'Retry' }).click()
  await page.waitForLoadState('networkidle')

  await expect(page.getByRole('button', { name: 'Retry' })).not.toBeVisible()
  await expect(page.getByText('Message that will fail')).toBeVisible()
})

test('scrolling to top loads entries from the previous week', async ({ page }) => {
  const eightDaysAgo = new Date(Date.now() - 8 * 24 * 60 * 60 * 1000).toISOString()
  await fetch(`${BACKEND}/test/seed-log-entry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: 'Old entry from last week', logged_at: eightDaysAgo, for_email: E2E_USER }),
  })

  // Send a current-week message so the list has content and isn't already scrolled to top
  await sendMessage(page, 'Current week message')

  // Old entry is outside the initial 7-day window
  await expect(page.getByText('Old entry from last week')).not.toBeVisible()

  // Scroll the message list to the top to trigger load-previous
  const listEl = page.locator('.overflow-y-auto').first()
  await listEl.evaluate((el) => {
    el.scrollTop = 0
    el.dispatchEvent(new Event('scroll'))
  })
  await page.waitForLoadState('networkidle')

  await expect(page.getByText('Old entry from last week')).toBeVisible()
})

test('pending badge count shows in chat header when a relation is pending', async ({ page }) => {
  await fetch('http://localhost:8000/test/seed-relation', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ peer_email: 'badge-test@example.com', label: 'friend', for_email: E2E_USER }),
  })

  await page.reload()
  await page.waitForLoadState('networkidle')

  const profileButton = page.getByRole('button', { name: /^Profile/ })
  await expect(profileButton).toBeVisible()
  // Badge shows a count > 0 (dev server seeds 1 relation on startup, test adds another)
  await expect(profileButton.locator('span')).toBeVisible()
})
