import { test as setup, expect } from '@playwright/test';

const ADMIN_EMAIL = 'admin@trendradar.com';
const ADMIN_PASSWORD = 'admin123456';
const DEMO_EMAIL = 'demo@test.com';
const DEMO_PASSWORD = 'demo123456';

setup('authenticate as admin', async ({ page }) => {
  await page.goto('/login');
  await page.getByPlaceholder('邮箱').fill(ADMIN_EMAIL);
  await page.getByPlaceholder('密码').fill(ADMIN_PASSWORD);
  await page.getByRole('button', { name: '登录' }).click();
  await page.waitForURL('**/dashboard', { timeout: 15000 });
  await page.context().storageState({ path: 'tests/e2e/.auth/admin.json' });
});

setup('authenticate as demo', async ({ page }) => {
  await page.goto('/login');
  await page.getByPlaceholder('邮箱').fill(DEMO_EMAIL);
  await page.getByPlaceholder('密码').fill(DEMO_PASSWORD);
  await page.getByRole('button', { name: '登录' }).click();
  await page.waitForURL('**/dashboard', { timeout: 15000 });
  await page.context().storageState({ path: 'tests/e2e/.auth/demo.json' });
});
