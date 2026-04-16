import { defineConfig } from '@playwright/test'

// The FastAPI backend must already be running on port 8000 before executing
// these tests. Start it with: cd backend && uv run python dev_server.py

export default defineConfig({
  globalSetup: './global-setup.ts',
  globalTeardown: './global-teardown.ts',
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
    command: 'npm run dev:e2e',
    cwd: '../frontend',
    port: 5173,
    reuseExistingServer: true,
    env: {
      VITE_OAUTH_ISSUER_URL: 'http://localhost:4444',
      VITE_GOOGLE_CLIENT_ID: 'e2e-client',
      VITE_API_URL: 'http://localhost:8000',
    },
  },
})
