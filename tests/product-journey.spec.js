const { test, expect } = require('@playwright/test');

test('home register login create persist logout login and mobile journey', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Water Tracker' })).toBeVisible();

  await page.getByRole('button', { name: 'Create account' }).click();
  await page.getByLabel('Email').fill('owner@example.test');
  await page.getByLabel('Password').fill('fixture-password');
  await page.getByRole('button', { name: 'Register' }).click();

  await page.getByLabel('Water amount (ml)').fill('500');
  await page.getByRole('button', { name: 'Add water' }).click();
  await expect(page.getByTestId('entries')).toContainText('500 ml');

  await page.getByRole('button', { name: 'Log out' }).click();
  await page.getByLabel('Email').fill('owner@example.test');
  await page.getByLabel('Password').fill('fixture-password');
  await page.getByRole('button', { name: 'Log in' }).click();
  await expect(page.getByTestId('entries')).toContainText('500 ml');

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('heading', { name: 'Today' })).toBeVisible();
  const fitsViewport = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
  expect(fitsViewport).toBe(true);
  await page.screenshot({ path: 'artifacts/quality/water-tracker-mobile.png', fullPage: true });
});
