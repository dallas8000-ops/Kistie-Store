import { defineConfig, devices } from '@playwright/test';

const isCI = Boolean(process.env.CI);
const demoMode = Boolean(process.env.PLAYWRIGHT_DEMO_SLOW);

export default defineConfig({
  testDir: './tests',
  timeout: demoMode ? 360000 : isCI ? 120000 : 360000,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:8000',
    headless: isCI ? true : false,
    slowMo: demoMode ? 2000 : 0,
    viewport: { width: 1280, height: 800 },
    video: 'off',
    screenshot: 'off',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        slowMo: demoMode ? 2000 : 0,
      },
    },
  ],
});
