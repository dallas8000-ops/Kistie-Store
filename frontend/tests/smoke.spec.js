import { test, expect } from '@playwright/test';

/**
 * Quick smoke suite: no staff credentials or seeded demo users required.
 * Run `npm run smoke` while Django listens on PLAYWRIGHT_BASE_URL (default http://127.0.0.1:8000).
 */
test.describe('smoke', () => {
  test('health returns JSON payload', async ({ request }) => {
    const res = await request.get('/health/?format=json');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.status).toBe('ok');
    expect(body.service).toBe('kistie-store');
  });

  test('root redirects to shop', async ({ request }) => {
    const res = await request.get('/', { maxRedirects: 0 });
    expect(res.status()).toBe(302);
    const loc = res.headers()['location'] || '';
    expect(loc).toMatch(/\/shop\/?$/);
  });

  test('shop page renders storefront', async ({ page }) => {
    await page.goto('/shop/');
    await expect(page).toHaveTitle(/Shop.*Kistie Store/);
    await expect(page.locator('#inventoryCurrency')).toBeVisible();
  });

  test('cart page loads for anonymous users', async ({ page }) => {
    await page.goto('/cart/');
    await expect(page.locator('h1')).toContainText('Your Cart');
  });

  test('checkout redirects empty cart to cart page', async ({ page }) => {
    await page.goto('/checkout/');
    await expect(page).toHaveURL(/\/cart\/?$/);
    await expect(page.locator('h1')).toContainText('Your Cart');
  });

  test('staff login page reachable', async ({ page }) => {
    await page.goto('/staff/login/');
    await expect(page.locator('h1')).toContainText('Staff sign in');
  });
});
