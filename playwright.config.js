process.env.PLAYWRIGHT_BROWSERS_PATH ||= '0';

const os = require('os');
const path = require('path');
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  outputDir: process.env.PALA_PLAYWRIGHT_OUTPUT || path.join(os.tmpdir(), 'pala-playwright-results'),
  reporter: [['line']],
  use: {
    screenshot: 'only-on-failure',
    trace: 'off',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
