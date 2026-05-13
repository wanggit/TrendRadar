import { test, expect } from '@playwright/test';

test.describe('Login Page', () => {
  test('should display login form', async ({ page }) => {
    await page.goto('/login');
    
    await expect(page).toHaveTitle(/TrendRadar/);
    await expect(page.getByPlaceholder('邮箱')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.getByRole('button', { name: '登录' })).toBeVisible();
  });

  test('should show validation error for empty form', async ({ page }) => {
    await page.goto('/login');
    
    await page.getByRole('button', { name: '登录' }).click();
    
    await expect(page.getByText('请输入邮箱')).toBeVisible();
    await expect(page.getByText('请输入密码')).toBeVisible();
  });

  test('should navigate to register page', async ({ page }) => {
    await page.goto('/login');
    
    await page.getByRole('link', { name: '立即注册' }).click();
    
    await expect(page).toHaveURL(/\/register/);
  });
});
