import { expect, test } from '@playwright/test';
import { ALL_ROUTES } from './routes';

for (const route of ALL_ROUTES) {
  test(`${route} loads without console errors or failed requests`, async ({ page }) => {
    const problems: string[] = [];
    page.on('console', (message) => {
      if (message.type() === 'error') problems.push(`console: ${message.text()}`);
    });
    page.on('pageerror', (error) => problems.push(`pageerror: ${error.message}`));
    page.on('requestfailed', (request) => problems.push(`request failed: ${request.url()}`));

    const response = await page.goto(route);
    expect(response?.status()).toBe(200);
    await expect(page.locator('h1').first()).toBeVisible();
    expect(problems).toEqual([]);
  });
}

test('an unknown path shows the not-found page', async ({ page }) => {
  const response = await page.goto('/no-such-page');
  expect(response?.status()).toBe(404);
  await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible();
});

test('log in leads to the dashboard', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email address').fill('zaeem@example.com');
  await page.getByLabel('Password', { exact: false }).first().fill('secret-pass');
  await page.getByRole('button', { name: 'Log in' }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
});

test('submitting an empty login shows an error summary that links to the fields', async ({
  page,
}) => {
  await page.goto('/login');
  await page.getByRole('button', { name: 'Log in' }).click();
  const summary = page.getByRole('alert').filter({ hasText: 'Please fix 2 problems' });
  await expect(summary).toBeVisible();
  await expect(summary).toBeFocused();
});
