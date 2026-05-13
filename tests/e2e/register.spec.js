import { test, expect } from '@playwright/test';

test.describe('Register Page', () => {
  test('should display registration form', async ({ page }) => {
    await page.goto('/register');
    
    await expect(page).toHaveTitle(/TrendRadar/);
    await expect(page.getByPlaceholder('邮箱')).toBeVisible();
    await expect(page.getByPlaceholder('昵称')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toHaveCount(2);
    await expect(page.getByRole('button', { name: '注册' })).toBeVisible();
  });

  test('should navigate to login page', async ({ page }) => {
    await page.goto('/register');
    
    await page.getByRole('link', { name: '立即登录' }).click();
    
    await expect(page).toHaveURL(/\/login/);
  });
});
