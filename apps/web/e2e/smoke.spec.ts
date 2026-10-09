import { expect, test } from '@playwright/test';

test.describe('AgriCarbon Atlas smoke', () => {
  test('landing page renders the core message and opens the workspace', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Understand your land');
    await expect(page.getByText('never issued carbon credits')).toBeVisible();
    await page.getByRole('link', { name: 'Open workspace' }).first().click();
    await expect(page).toHaveURL(/\/app/);
    await expect(page.getByRole('heading', { name: 'Selected plot details' })).toBeVisible();
  });

  test('workspace falls back to demo data when the API is offline', async ({ page }) => {
    await page.route('**/api/v1/**', (route) => route.abort('connectionrefused'));
    await page.goto('/app');
    await expect(page.getByText('API offline')).toBeVisible();
    await expect(page.getByText('Demo mango orchard', { exact: false }).first()).toBeVisible();
    await expect(page.getByRole('link', { name: 'See carbon potential' })).toBeVisible();
    await expect(page.getByRole('toolbar', { name: 'Mark your land' })).toBeVisible();
  });

  test('the header Import button opens the Import data dialog from any page', async ({ page }) => {
    await page.goto('/app/data');
    await page.getByRole('button', { name: 'Import data' }).click();
    await expect(page.getByRole('heading', { name: 'Import data' })).toBeVisible();
    await expect(page.getByText('Only the results are kept — the file itself is not stored.')).toBeVisible();
  });

  test('old 4D cube links land on the results page', async ({ page }) => {
    await page.goto('/app/plots/PLT-DEMOIN/cube');
    await expect(page).toHaveURL(/\/app\/plots\/PLT-DEMOIN\/results$/);
  });
});
