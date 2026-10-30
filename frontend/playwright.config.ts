import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  reporter: [['list']],
  use: { baseURL: 'http://localhost:3100', trace: 'retain-on-failure' },
  projects: [
    {
      name: 'e2e',
      testIgnore: /parity\//,
      use: { ...devices['Desktop Chrome'], trace: 'off' },
    },
    {
      name: 'parity',
      testMatch: /parity\/.*\.spec\.ts/,
      timeout: 120_000,
      use: {
        ...devices['Desktop Chrome'],
        reducedMotion: 'reduce',
        deviceScaleFactor: 1,
        // Software, non-partial rasterisation: GPU tiling made rounded-corner edge pixels flicker
        // between identical renders (design vs design), which would hide real regressions.
        launchOptions: { args: ['--disable-gpu', '--disable-partial-raster'] },
      },
    },
  ],
  // The parity self-check (design vs design) needs no server; PARITY_SELF=1 skips it.
  webServer: process.env.PARITY_SELF
    ? undefined
    : {
        command: 'pnpm start -p 3100',
        url: 'http://localhost:3100/login',
        reuseExistingServer: true,
        timeout: 120_000,
      },
});
