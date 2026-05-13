import { test, expect } from '@playwright/test';

test.describe('Users Management - Admin Access', () => {
  test.use({ storageState: 'tests/e2e/.auth/admin.json' });

  test('admin should see user management menu item', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('menuitem', { name: '用户管理' })).toBeVisible();
  });

  test('admin can navigate to users page', async ({ page }) => {
    await page.goto('/dashboard');
    await page.getByRole('menuitem', { name: '用户管理' }).click();
    await page.waitForURL('**/users', { timeout: 10000 });
    await expect(page.locator('.users-management-page')).toBeVisible();
  });
});

test.describe('Users Management - Non-Admin Access', () => {
  test.use({ storageState: 'tests/e2e/.auth/demo.json' });

  test('non-admin should not see user management menu item', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('menuitem', { name: '用户管理' })).not.toBeVisible();
  });

  test('non-admin should be redirected from users page', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/dashboard', { timeout: 5000 });
    await expect(page).toHaveURL(/\/dashboard/);
  });
});

test.describe('Users Management - User List', () => {
  test.use({ storageState: 'tests/e2e/.auth/admin.json' });

  test('should display users management page', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await expect(page.locator('.users-management-page')).toBeVisible();
    await expect(page.getByRole('button', { name: '添加用户' })).toBeVisible();
  });

  test('should display users table', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await expect(page.locator('.el-table')).toBeVisible();
  });

  test('should display existing users in table', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await page.waitForTimeout(2000);
    await expect(page.locator('.el-table__body tr').first()).toBeVisible();
    await expect(page.locator('text=admin@trendradar.com')).toBeVisible();
  });

  test('should display pagination', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await expect(page.locator('.el-pagination')).toBeVisible();
  });
});

test.describe('Users Management - Search', () => {
  test.use({ storageState: 'tests/e2e/.auth/admin.json' });

  test('should have search input', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await expect(page.getByPlaceholder('搜索邮箱或昵称')).toBeVisible();
  });

  test('should search by email', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await page.getByPlaceholder('搜索邮箱或昵称').fill('admin@trendradar.com');
    await page.getByPlaceholder('搜索邮箱或昵称').press('Enter');
    await page.waitForTimeout(1500);
    await expect(page.locator('text=admin@trendradar.com')).toBeVisible();
  });
});

test.describe('Users Management - Create User', () => {
  test.use({ storageState: 'tests/e2e/.auth/admin.json' });

  test('should open add user dialog', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await page.getByRole('button', { name: '添加用户' }).click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    await expect(page.locator('.el-dialog__title')).toContainText('添加用户');
  });

  test('should show all form items in add dialog', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await page.getByRole('button', { name: '添加用户' }).click();
    await expect(page.locator('.el-form-item:has-text("邮箱")')).toBeVisible();
    await expect(page.locator('.el-form-item:has-text("昵称")')).toBeVisible();
    await expect(page.locator('.el-form-item:has-text("密码")')).toBeVisible();
    await expect(page.locator('.el-form-item:has-text("套餐")')).toBeVisible();
    await expect(page.locator('.el-form-item:has-text("状态")')).toBeVisible();
    await expect(page.locator('.el-form-item:has-text("超级管理员")')).toBeVisible();
  });

  test('should create a new user successfully', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    const testEmail = `test-${Date.now()}@example.com`;
    await page.getByRole('button', { name: '添加用户' }).click();
    await page.getByLabel('邮箱').fill(testEmail);
    await page.getByLabel('昵称').fill('测试用户');
    await page.getByLabel('密码').fill('testpass123');
    await page.getByRole('button', { name: '创建' }).click();
    await page.waitForTimeout(2000);

    // Search for the newly created user
    await page.locator('input[placeholder="搜索邮箱或昵称"]').fill(testEmail);
    await page.locator('input[placeholder="搜索邮箱或昵称"]').press('Enter');
    await page.waitForTimeout(1000);
    await expect(page.locator(`text=${testEmail}`)).toBeVisible({ timeout: 10000 });
  });

  test('should show validation error for invalid email', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await page.getByRole('button', { name: '添加用户' }).click();
    await page.getByLabel('邮箱').fill('invalid-email');
    await page.getByLabel('邮箱').blur();
    await expect(page.locator('text=请输入有效的邮箱地址')).toBeVisible();
  });

  test('should show validation error for short password', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await page.getByRole('button', { name: '添加用户' }).click();
    await page.getByLabel('邮箱').fill(`test-${Date.now()}@example.com`);
    await page.getByLabel('密码').fill('short');
    await page.getByLabel('密码').blur();
    await expect(page.locator('text=密码至少8位')).toBeVisible();
  });

  test('should select tier in add dialog', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await page.getByRole('button', { name: '添加用户' }).click();
    await page.locator('.el-form-item:has-text("套餐") .el-select').click();
    await expect(page.getByRole('option', { name: 'Free' })).toBeVisible();
    await expect(page.getByRole('option', { name: 'Pro' })).toBeVisible();
    await expect(page.getByRole('option', { name: 'Enterprise' })).toBeVisible();
    await page.keyboard.press('Escape');
  });

  test('should select status in add dialog', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await page.getByRole('button', { name: '添加用户' }).click();
    await page.locator('.el-form-item:has-text("状态") .el-select').click();
    await page.waitForTimeout(500);
    await expect(page.getByRole('option', { name: 'Active' }).first()).toBeVisible();
    await page.keyboard.press('Escape');
  });
});

test.describe('Users Management - Edit User', () => {
  test.use({ storageState: 'tests/e2e/.auth/admin.json' });

  test('should open edit dialog when clicking edit button', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await page.waitForTimeout(1000);
    await page.locator('text=admin@trendradar.com').hover();
    const row = page.locator('.el-table__body tr:has-text("admin@trendradar.com")');
    await row.getByRole('button', { name: '编辑' }).click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    await expect(page.locator('.el-dialog__title')).toContainText('编辑用户');
  });

  test('should not show email field in edit dialog', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await page.waitForTimeout(1000);
    const row = page.locator('.el-table__body tr:has-text("admin@trendradar.com")');
    await row.getByRole('button', { name: '编辑' }).click();
    await expect(page.locator('.el-form-item:has-text("邮箱")')).not.toBeVisible();
  });

  test('should update user tier', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    const testEmail = `edit-test-${Date.now()}@example.com`;
    await page.getByRole('button', { name: '添加用户' }).click();
    await page.getByLabel('邮箱').fill(testEmail);
    await page.getByLabel('昵称').fill('编辑测试用户');
    await page.getByLabel('密码').fill('testpass123');
    await page.getByRole('button', { name: '创建' }).click();
    await page.waitForTimeout(3000);

    // Search for the newly created user
    await page.locator('input[placeholder="搜索邮箱或昵称"]').fill(testEmail);
    await page.locator('input[placeholder="搜索邮箱或昵称"]').press('Enter');
    await page.waitForTimeout(1000);
    await expect(page.locator(`text=${testEmail}`).first()).toBeVisible({ timeout: 10000 });

    const row = page.locator(`.el-table__body tr:has-text("${testEmail}")`).first();
    await row.getByRole('button', { name: '编辑' }).click();
    await page.waitForTimeout(1000);
    await page.locator('.el-form-item:has-text("套餐") .el-select').click();
    await page.getByRole('option', { name: 'Pro' }).first().click();
    await page.getByRole('button', { name: '保存' }).click();
    await page.waitForTimeout(2000);
    await expect(page.locator('text=用户更新成功').first()).toBeVisible({ timeout: 10000 });
  });

  test('should update user status', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    const testEmail = `status-test-${Date.now()}@example.com`;
    await page.getByRole('button', { name: '添加用户' }).click();
    await page.getByLabel('邮箱').fill(testEmail);
    await page.getByLabel('昵称').fill('状态测试用户');
    await page.getByLabel('密码').fill('testpass123');
    await page.getByRole('button', { name: '创建' }).click();
    await page.waitForTimeout(3000);

    // Search for the newly created user
    await page.locator('input[placeholder="搜索邮箱或昵称"]').fill(testEmail);
    await page.locator('input[placeholder="搜索邮箱或昵称"]').press('Enter');
    await page.waitForTimeout(1000);
    await expect(page.locator(`text=${testEmail}`).first()).toBeVisible({ timeout: 10000 });

    const row = page.locator(`.el-table__body tr:has-text("${testEmail}")`).first();
    await row.getByRole('button', { name: '编辑' }).click();
    await page.waitForTimeout(1000);
    await page.locator('.el-form-item:has-text("状态") .el-select').click();
    await page.getByRole('option', { name: 'Inactive' }).first().click();
    await page.getByRole('button', { name: '保存' }).click();
    await page.waitForTimeout(2000);
    await expect(page.locator('text=用户更新成功').first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Users Management - Delete User', () => {
  test.use({ storageState: 'tests/e2e/.auth/admin.json' });

  test('should delete a user after confirmation', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    const testEmail = `delete-test-${Date.now()}@example.com`;
    await page.getByRole('button', { name: '添加用户' }).click();
    await page.getByLabel('邮箱').fill(testEmail);
    await page.getByLabel('昵称').fill('删除测试用户');
    await page.getByLabel('密码').fill('testpass123');
    await page.getByRole('button', { name: '创建' }).click();
    await page.waitForTimeout(3000);

    // Search for the newly created user
    await page.locator('input[placeholder="搜索邮箱或昵称"]').fill(testEmail);
    await page.locator('input[placeholder="搜索邮箱或昵称"]').press('Enter');
    await page.waitForTimeout(1000);
    await expect(page.locator(`text=${testEmail}`).first()).toBeVisible({ timeout: 10000 });

    const row = page.locator(`.el-table__body tr:has-text("${testEmail}")`).first();
    await row.getByRole('button', { name: '删除' }).click();
    await page.getByRole('button', { name: '确定' }).click();
    await page.waitForTimeout(2000);
    
    // Reload page to verify deletion
    await page.reload();
    await page.waitForURL('**/users', { timeout: 10000 });
    await page.waitForTimeout(2000);
    await expect(page.locator(`text=${testEmail}`)).toHaveCount(0, { timeout: 10000 });
  });

  test('should not allow admin to delete themselves', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await page.waitForTimeout(2000);
    const row = page.locator('.el-table__body tr:has-text("admin@trendradar.com")').first();
    await row.getByRole('button', { name: '删除' }).click();
    await page.getByRole('button', { name: '确定' }).click();
    await page.waitForTimeout(2000);
    await expect(page.locator('text=Cannot delete yourself').first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Users Management - Reset Password', () => {
  test.use({ storageState: 'tests/e2e/.auth/admin.json' });

  test('should reset user password', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    const testEmail = `reset-test-${Date.now()}@example.com`;
    await page.getByRole('button', { name: '添加用户' }).click();
    await page.getByLabel('邮箱').fill(testEmail);
    await page.getByLabel('昵称').fill('密码重置测试用户');
    await page.getByLabel('密码').fill('testpass123');
    await page.getByRole('button', { name: '创建' }).click();
    await page.waitForTimeout(3000);

    // Search for the newly created user
    await page.locator('input[placeholder="搜索邮箱或昵称"]').fill(testEmail);
    await page.locator('input[placeholder="搜索邮箱或昵称"]').press('Enter');
    await page.waitForTimeout(1000);
    await expect(page.locator(`text=${testEmail}`).first()).toBeVisible({ timeout: 10000 });

    const row = page.locator(`.el-table__body tr:has-text("${testEmail}")`).first();
    await row.getByRole('button', { name: '重置密码' }).click();
    await page.getByRole('button', { name: '确定' }).click();
    await page.waitForTimeout(2000);
    await expect(page.locator('text=Password reset successfully').first()).toBeVisible({ timeout: 10000 });
  });

  test('should not allow admin to reset their own password via admin', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await page.waitForTimeout(2000);
    const row = page.locator('.el-table__body tr:has-text("admin@trendradar.com")').first();
    await row.getByRole('button', { name: '重置密码' }).click();
    await page.getByRole('button', { name: '确定' }).click();
    await page.waitForTimeout(2000);
    await expect(page.locator('text=Cannot reset your own password').first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Users Management - User Display', () => {
  test.use({ storageState: 'tests/e2e/.auth/admin.json' });

  test('should display tier tags', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await page.waitForTimeout(1000);
    await expect(page.locator('.el-tag:has-text("enterprise")')).toBeVisible();
  });

  test('should display status tags', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await page.waitForTimeout(1000);
    await expect(page.locator('.el-tag:has-text("active")').first()).toBeVisible();
  });

  test('should display superuser indicator', async ({ page }) => {
    await page.goto('/users');
    await page.waitForURL('**/users', { timeout: 10000 });
    await page.waitForTimeout(1000);
    const row = page.locator('.el-table__body tr:has-text("admin@trendradar.com")');
    await expect(row.locator('text=是')).toBeVisible();
  });
});
