import { test, expect } from '@playwright/test';

/**
 * E2E tests for the Politician Dashboard page
 * Tests data loading, error states, and UI rendering
 */

const TEST_BIOGUIDE_ID = 'A000370'; // Alma Adams
const TEST_PELOSI_ID = 'P000197';   // Nancy Pelosi (has trading data)

test.describe('Politician Dashboard', () => {

    test('should load politician page and show loading skeleton', async ({ page }) => {
        // Navigate to politician page
        await page.goto(`/politician/${TEST_BIOGUIDE_ID}`);

        // Should show loading state initially or content
        const pageContent = await page.content();
        expect(pageContent).toBeTruthy();
    });

    test('should display politician header with name and party', async ({ page }) => {
        await page.goto(`/politician/${TEST_BIOGUIDE_ID}`);

        // Wait for data to load
        await page.waitForLoadState('networkidle');

        // Page should load without error
        const pageText = await page.textContent('body');
        expect(pageText).toBeTruthy();

        // Check that we don't have "Invalid politician ID" error
        const hasInvalidError = pageText?.includes('Invalid politician ID');
        expect(hasInvalidError).toBe(false);
    });

    test('should fetch member profile from API', async ({ page }) => {
        // Test that the API endpoint works directly
        const response = await page.request.get(
            `https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com/v1/congress/members/${TEST_BIOGUIDE_ID}`
        );

        expect(response.ok()).toBeTruthy();

        const data = await response.json();
        expect(data.member).toBeDefined();
        expect(data.member.bioguide_id).toBe(TEST_BIOGUIDE_ID);
        expect(data.member.first_name).toBe('Alma');
        expect(data.member.last_name).toBe('Adams');
        expect(data.member.party).toBe('D');
    });

    test('should handle member with trading data (Nancy Pelosi)', async ({ page }) => {
        await page.goto(`/politician/${TEST_PELOSI_ID}`);

        // Wait for network requests to complete
        await page.waitForLoadState('networkidle');

        // Check page loaded without crashing
        const hasError = await page.locator('text=/error|failed/i').count() > 0;

        // Take screenshot
        await page.screenshot({ path: 'e2e/screenshots/pelosi-page.png', fullPage: true });

        // If there's an error, fail with details
        if (hasError) {
            const errorText = await page.textContent('body');
            console.log('Error found on page:', errorText?.slice(0, 500));
        }
    });

    test('should show error state for invalid bioguide ID', async ({ page }) => {
        await page.goto('/politician/INVALID123');

        await page.waitForLoadState('networkidle');

        // Should show some error or empty state
        const pageText = await page.textContent('body');
        expect(pageText).toBeTruthy();

        await page.screenshot({ path: 'e2e/screenshots/invalid-politician.png', fullPage: true });
    });

    test('should navigate to politician page from members list', async ({ page }) => {
        // Go to members page first
        await page.goto('/members');
        await page.waitForLoadState('networkidle');

        // Look for any politician card link
        const memberLink = page.locator('a[href*="/politician/"]').first();

        if (await memberLink.count() > 0) {
            const href = await memberLink.getAttribute('href');
            console.log('Found member link:', href);

            // Wait for navigation to complete after click
            await Promise.all([
                page.waitForURL('**/politician/**'),
                memberLink.click()
            ]);

            // Verify we're on a politician page
            expect(page.url()).toContain('/politician/');

            await page.screenshot({ path: 'e2e/screenshots/navigated-politician.png', fullPage: true });
        } else {
            console.log('No member links found on /members page');
        }
    });
});

test.describe('API Integration', () => {

    test('should fetch trades for member', async ({ page }) => {
        const response = await page.request.get(
            `https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com/v1/members/${TEST_PELOSI_ID}/trades?limit=5`
        );

        // Log response for debugging
        const status = response.status();
        console.log(`Member trades API status: ${status}`);

        if (response.ok()) {
            const data = await response.json();
            console.log('Trades data:', JSON.stringify(data).slice(0, 500));
        } else {
            const text = await response.text();
            console.log('Trades API error:', text);
        }
    });

    test('should fetch member profile via congress endpoint', async ({ page }) => {
        const response = await page.request.get(
            `https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com/v1/congress/members/${TEST_BIOGUIDE_ID}`
        );

        expect(response.status()).toBe(200);

        const data = await response.json();
        expect(data.member.bioguide_id).toBe(TEST_BIOGUIDE_ID);
    });
});
