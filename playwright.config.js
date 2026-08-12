process.env.PLAYWRIGHT_BROWSERS_PATH ||= '0';

const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  outputDir: './artifacts/quality/playwright-results',
  reporter: [
    ['line'],
    ['html', { outputFolder: './artifacts/quality/playwright-report', open: 'never' }],
    ['json', { outputFile: './artifacts/quality/playwright-report/results.json' }],
  ],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'py -3 -m http.server 4173 --bind 127.0.0.1 --directory fixtures/water-tracker',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
