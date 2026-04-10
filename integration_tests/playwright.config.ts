import { defineConfig } from '@playwright/test'

// The FastAPI backend must already be running on port 8000 before executing
// these tests. Start it with: cd backend && uv run python dev_server.py

export default defineConfig({
  testDir: './tests',
  retries: 0,
  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
  webServer: {
    command: 'npm run dev',
    cwd: '../frontend',
    port: 5173,
    reuseExistingServer: true,
  },
})
