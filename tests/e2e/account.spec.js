import { test, expect } from '@playwright/test';

const DEFAULT_EMAIL = 'demo@test.com';
const DEFAULT_PASSWORD = 'demo123456';

async function loginAndNavigateToAccount(page) {
  await page.goto('/login');
  await page.getByPlaceholder('邮箱').fill(DEFAULT_EMAIL);
  await page.locator('input[type="password"]').fill(DEFAULT_PASSWORD);
  await page.getByRole('button', { name: '登录' }).click();
  await page.waitForURL('**/dashboard', { timeout: 15000 });
  await page.getByRole('menuitem', { name: '账户设置' }).click();
  await page.waitForURL('**/account', { timeout: 15000 });
}

test.describe('Account Page - Profile Display', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToAccount(page);
  });

  test('should display account page', async ({ page }) => {
    await expect(page.getByText('账户信息')).toBeVisible();
  });

  test('should display user email', async ({ page }) => {
    await expect(page.getByText('邮箱')).toBeVisible();
    await expect(page.getByText(DEFAULT_EMAIL)).toBeVisible();
  });

  test('should display user nickname', async ({ page }) => {
    await expect(page.getByText('昵称')).toBeVisible();
  });

  test('should display user tier', async ({ page }) => {
    await expect(page.getByText('套餐')).toBeVisible();
    const tierTag = page.locator('.el-descriptions__body').locator('tr').nth(2).locator('.el-tag');
    await expect(tierTag).toBeVisible();
  });

  test('should display user status', async ({ page }) => {
    await expect(page.getByText('状态')).toBeVisible();
  });

  test('should display registration time', async ({ page }) => {
    await expect(page.getByText('注册时间')).toBeVisible();
    const timeValue = page.locator('.el-descriptions__body td').last();
    await expect(timeValue).toBeVisible();
  });
});

test.describe('Account Page - Change Password', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToAccount(page);
  });

  test('should display change password section', async ({ page }) => {
    await expect(page.getByText('修改密码')).toBeVisible();
  });

  test('should display current password field', async ({ page }) => {
    await expect(page.getByText('当前密码')).toBeVisible();
    const currentPasswordInput = page.locator('.el-form-item').filter({ hasText: '当前密码' }).locator('input');
    await expect(currentPasswordInput).toBeVisible();
  });

  test('should display new password field', async ({ page }) => {
    await expect(page.locator('.el-form-item__label').filter({ hasText: '新密码' })).toBeVisible();
    const newPasswordInput = page.locator('.el-form-item').filter({ hasText: '新密码' }).locator('input');
    await expect(newPasswordInput).toBeVisible();
  });

  test('should display update password button', async ({ page }) => {
    await expect(page.getByRole('button', { name: '更新密码' })).toBeVisible();
  });

  test('should show validation error for empty current password', async ({ page }) => {
    const newPasswordInput = page.locator('.el-form-item').filter({ hasText: '新密码' }).locator('input');
    await newPasswordInput.fill('newpass123');
    await page.getByRole('button', { name: '更新密码' }).click();
    await expect(page.getByText('请输入当前密码')).toBeVisible();
  });

  test('should show validation error for empty new password', async ({ page }) => {
    const currentPasswordInput = page.locator('.el-form-item').filter({ hasText: '当前密码' }).locator('input');
    await currentPasswordInput.fill('demo123456');
    await page.getByRole('button', { name: '更新密码' }).click();
    await expect(page.getByText('请输入新密码')).toBeVisible();
  });

  test('should show validation error for short new password', async ({ page }) => {
    const currentPasswordInput = page.locator('.el-form-item').filter({ hasText: '当前密码' }).locator('input');
    const newPasswordInput = page.locator('.el-form-item').filter({ hasText: '新密码' }).locator('input');
    await currentPasswordInput.fill('demo123456');
    await newPasswordInput.fill('short');
    await newPasswordInput.blur();
    await expect(page.getByText('密码至少 8 位')).toBeVisible();
  });
});
