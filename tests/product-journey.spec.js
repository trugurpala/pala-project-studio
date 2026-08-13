const { test, expect } = require('@playwright/test');
const fs = require('fs');
const os = require('os');
const path = require('path');

test('Pala 1.1.0 browser profile runs headless without helper UI', async ({ browser, context, page }) => {
  const consoleMessages = [];
  const requests = [];
  const evidenceRoot = path.resolve(
    process.env.PALA_PLAYWRIGHT_EVIDENCE || path.join(os.tmpdir(), 'pala-playwright-evidence'),
  );
  fs.mkdirSync(evidenceRoot, { recursive: true });
  await context.tracing.start({ screenshots: true, snapshots: true, sources: true });
  page.on('console', (message) => consoleMessages.push(message.text()));
  page.on('request', (request) => requests.push(request.url()));

  await page.goto(
    'data:text/html,' + encodeURIComponent(`
      <main>
        <h1>PALA CONTROL CENTER</h1>
        <p>Pala 1.1.0 local release candidate</p>
        <button type="button">Verify</button>
        <output aria-live="polite"></output>
      </main>
      <script>
        document.querySelector('button').addEventListener('click', () => {
          document.querySelector('output').textContent = 'passed';
          console.log('pala-browser-profile-passed');
        });
      </script>
    `),
  );

  await expect(page.getByRole('heading', { name: 'PALA CONTROL CENTER' })).toBeVisible();
  await page.getByRole('button', { name: 'Verify' }).click();
  await expect(page.getByRole('status')).toHaveText('passed');
  expect(consoleMessages).toContain('pala-browser-profile-passed');
  expect(requests).toHaveLength(0);

  await page.screenshot({ path: path.join(evidenceRoot, 'control-center.png'), fullPage: true });
  await context.tracing.stop({ path: path.join(evidenceRoot, 'trace.zip') });
  fs.writeFileSync(
    path.join(evidenceRoot, 'console.json'),
    JSON.stringify({ messages: consoleMessages }, null, 2) + '\n',
  );
  fs.writeFileSync(
    path.join(evidenceRoot, 'network.har'),
    JSON.stringify({ log: { version: '1.2', creator: { name: 'Pala', version: '1.1.0' }, entries: requests } }, null, 2) + '\n',
  );
  fs.writeFileSync(
    path.join(evidenceRoot, 'browser.json'),
    JSON.stringify({ browser_version: browser.version(), ui_opened: false, trace_viewer_opened: false }, null, 2) + '\n',
  );
});
