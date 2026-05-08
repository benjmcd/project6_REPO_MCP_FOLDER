// @ts-check
import { defineConfig, devices } from '@playwright/test';

const SERVER_PORT = 8031;
const PYTHON = process.env.PLAYWRIGHT_PYTHON
  || (process.platform === 'win32' ? 'py -3.12' : 'python3');

/**
 * Read environment variables from file.
 * https://github.com/motdotla/dotenv
 */
// import dotenv from 'dotenv';
// import path from 'path';
// dotenv.config({ path: path.resolve(__dirname, '.env') });

/**
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e',
  testIgnore: ['**/example.spec.js'],
  /* Run tests in files in sequence because they share one isolated test harness. */
  fullyParallel: false,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* The review/browser flow is stateful enough that one worker is the safest baseline. */
  workers: 1,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [['html', { open: 'never' }]],
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    baseURL: `http://127.0.0.1:${SERVER_PORT}`,

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: {
    command: `${PYTHON} -m uvicorn review_browser_server:create_app --factory --host 127.0.0.1 --port ${SERVER_PORT}`,
    cwd: './backend/tests',
    env: {
      DB_INIT_MODE: 'none',
      LAYER3_SIGNED_REFERENCE_SECRET: 'playwright-layer3-signed-reference-secret',
    },
    url: `http://127.0.0.1:${SERVER_PORT}/health`,
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});

