import { test, expect } from '@playwright/test';

test.describe('Smoke Tests - Core Pages', () => {
    test('homepage/dashboard loads successfully', async ({ page }) => {
        await page.goto('/');
        await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
    });

    test('bills page loads successfully', async ({ page }) => {
        await page.goto('/bills');
        await expect(page.getByRole('heading', { name: /bills/i })).toBeVisible();
    });

    test('lobbying page loads successfully', async ({ page }) => {
        await page.goto('/lobbying');
        await expect(page.getByRole('heading', { name: /lobbying/i })).toBeVisible();
    });

    test('members page loads successfully', async ({ page }) => {
        await page.goto('/members');
        await expect(page.getByRole('heading', { name: /members/i })).toBeVisible();
    });
});
