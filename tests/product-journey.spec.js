const { test, expect } = require('@playwright/test');
const { execFileSync, spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { pathToFileURL } = require('url');

function pythonLauncher(environment = process.env, platform = process.platform) {
  if (environment.PALA_PYTHON) {
    return { command: environment.PALA_PYTHON, args: [] };
  }
  if (platform === 'win32') {
    return { command: 'py', args: ['-3'] };
  }
  return spawnSync('python3', ['--version'], { stdio: 'ignore' }).status === 0
    ? { command: 'python3', args: [] }
    : { command: 'python', args: [] };
}

test('generated Pala 1.2.0 Control Center passes real local browser checks', async ({ browser, context, page }) => {
  const consoleMessages = [];
  const requests = [];
  const repository = path.resolve(__dirname, '..');
  const projectRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'pala-control-center-project-'));
  const pagePath = path.join(projectRoot, 'control-center.html');
  const evidenceRoot = path.resolve(
    process.env.PALA_PLAYWRIGHT_EVIDENCE || path.join(os.tmpdir(), 'pala-playwright-evidence'),
  );
  fs.mkdirSync(evidenceRoot, { recursive: true });
  const privatePath = ['C:', 'Users', 'Owner', 'private.txt'].join('\\');
  const privateFinding = ['Authorization', 'Bearer'].join(': ') + ' ' + ['top', 'secret', 'value'].join('-');
  const snapshot = {
    project: 'Pala browser fixture', state: 'VERIFYING', acceptance_verified: 1, acceptance_total: 2,
    quality: 'blocked', environment: 'local', delivery: 'not-run', live_verification: 'not-run',
    blocker: 'Quality evidence is pending', next_action: 'Run the required check', owner_request: 'Nothing',
    product_version: '1.2.0',
    queue: { items: [{ ticket: 'M80-T4', status: 'IN_PROGRESS' }], can_complete: false },
    context_receipts: { items: [{ validation_status: 'passed', receipt_id: 'receipt-safe' }], can_complete: false },
    project_history: { items: [{ lifecycle: 'project-closed', summary: 'safe bounded history' }], can_complete: false },
    failure_intelligence: { items: [{ failure_class: 'timeout', resolution_state: 'OBSERVED' }], findings: [privateFinding], can_complete: false },
    profiles: { items: [{ profile_kind: 'public-release', risk_level: 'high' }], can_complete: false },
    host_capabilities: { items: [{ capability_id: 'local_read', status: 'passed' }], can_complete: false },
    host_processes: { items: [{ status: 'not-run', authority: 'RuntimeObservations/read-only' }], can_complete: false },
    security_release: { items: [{ quality: 'blocked', delivery: 'not-assessed' }], findings: [privatePath], can_complete: false },
  };
  const python = pythonLauncher();
  execFileSync(
    python.command,
    [
      ...python.args,
      '-c',
      "import json,sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from pala_owner_cockpit import render_owner_cockpit;from pala_view import render;snapshot=json.loads(sys.argv[4]);page=render({'root_name':'Pala browser fixture','stamp':'2026-08-15','next_action':'Run the required check','owner_cockpit_html':render_owner_cockpit(snapshot,fragment=True)},freshness_fn=lambda _:'fresh');Path(sys.argv[3]).write_text(page,encoding='utf-8')",
      path.join(repository, 'scripts'),
      projectRoot,
      pagePath,
      JSON.stringify(snapshot),
    ],
    { cwd: repository, stdio: 'pipe' },
  );

  await context.tracing.start({ screenshots: true, snapshots: true, sources: true });
  page.on('console', (message) => consoleMessages.push({ type: message.type(), text: message.text() }));
  page.on('request', (request) => requests.push(request.url()));
  await context.setOffline(true);
  await page.goto(pathToFileURL(pagePath).href);

  const skipText = String.fromCodePoint(0x130, 0x00e7, 0x65, 0x72, 0x69, 0x11f, 0x65, 0x20, 0x67, 0x65, 0x00e7);
  const themeText = String.fromCodePoint(0x41, 0x00e7, 0x131, 0x6b, 0x20, 0x74, 0x65, 0x6d, 0x61);
  const skipLink = page.getByRole('link', { name: skipText });
  await skipLink.focus();
  await expect(skipLink).toBeFocused();
  await expect(skipLink).toHaveText(skipText);
  await expect(page.getByRole('heading', { name: /Pala Kontrol Merkezi/ }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: themeText })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'PALA CONTROL CENTER' })).toBeVisible();
  await expect(page.getByText('Pala 1.2.0', { exact: false }).first()).toBeVisible();
  for (const label of ['Queue', 'Receipts', 'Failure Intelligence', 'Profiles', 'Host Capabilities', 'Host & Processes', 'Security & Release']) {
    await expect(page.getByRole('link', { name: label })).toBeVisible();
  }
  expect(await page.locator('.pala-control-center').getAttribute('data-can-complete')).toBe('false');
  await expect(page.getByText('M80-T4')).toBeVisible();
  await expect(page.getByText('private value hidden').first()).toBeVisible();
  expect(await page.content()).not.toContain(privatePath);
  expect(await page.content()).not.toContain('top-secret-value');
  await page.getByRole('link', { name: 'Queue' }).focus();
  await expect(page.getByRole('link', { name: 'Queue' })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Receipts' })).toBeFocused();
  await page.setViewportSize({ width: 1440, height: 900 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
  await page.setViewportSize({ width: 390, height: 844 });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow).toBe(false);
  const reducedMotionRule = await page.locator('style').allTextContents();
  expect(reducedMotionRule.join('\n')).toContain('prefers-reduced-motion');
  expect(requests.filter((url) => /^https?:/i.test(url))).toHaveLength(0);
  expect(consoleMessages.filter((message) => message.type === 'error')).toEqual([]);

  await page.screenshot({ path: path.join(evidenceRoot, 'control-center.png'), fullPage: true });
  await context.tracing.stop({ path: path.join(evidenceRoot, 'trace.zip') });
  fs.writeFileSync(
    path.join(evidenceRoot, 'console.json'),
    JSON.stringify({ messages: consoleMessages }, null, 2) + '\n',
  );
  fs.writeFileSync(
    path.join(evidenceRoot, 'network.har'),
    JSON.stringify({ log: { version: '1.2', creator: { name: 'Pala', version: '1.2.0' }, entries: requests } }, null, 2) + '\n',
  );
  fs.writeFileSync(
    path.join(evidenceRoot, 'browser.json'),
    JSON.stringify({ browser_version: browser.version(), generated_page: true, ui_opened: false }, null, 2) + '\n',
  );
});
