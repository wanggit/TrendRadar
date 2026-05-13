import { test, expect } from '@playwright/test';

const DEFAULT_EMAIL = 'demo@test.com';
const DEFAULT_PASSWORD = 'demo123456';

async function loginAndNavigateToOrders(page) {
  await page.goto('/login');
  await page.getByPlaceholder('邮箱').fill(DEFAULT_EMAIL);
  await page.locator('input[type="password"]').fill(DEFAULT_PASSWORD);
  await page.getByRole('button', { name: '登录' }).click();
  await page.waitForURL('**/dashboard', { timeout: 15000 });
  await page.getByRole('menuitem', { name: '订单记录' }).click();
  await page.waitForURL('**/orders', { timeout: 15000 });
}

test.describe('Orders Page - Layout', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToOrders(page);
  });

  test('should display orders page title', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '订单历史' })).toBeVisible();
  });
});

test.describe('Orders Page - Orders Table', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToOrders(page);
  });

  test('should display orders table', async ({ page }) => {
    await expect(page.locator('.el-table')).toBeVisible();
  });

  test('should display table columns', async ({ page }) => {
    await expect(page.getByText('订单号')).toBeVisible();
    await expect(page.getByText('产品')).toBeVisible();
    await expect(page.getByText('金额')).toBeVisible();
    await expect(page.getByText('支付方式')).toBeVisible();
    await expect(page.getByText('状态')).toBeVisible();
    await expect(page.getByText('创建时间')).toBeVisible();
    await expect(page.getByText('支付时间')).toBeVisible();
  });
});

test.describe('Orders Page - Empty State', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToOrders(page);
  });

  test('should display empty state when no orders', async ({ page }) => {
    await page.waitForTimeout(2000);
    const emptyState = page.locator('.el-empty');
    const isVisible = await emptyState.isVisible().catch(() => false);
    if (isVisible) {
      await expect(page.getByText('暂无订单记录')).toBeVisible();
    }
  });
});

test.describe('Orders Page - Order Display', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToOrders(page);
  });

  test('should display product type labels', async ({ page }) => {
    await page.waitForTimeout(2000);
    const table = page.locator('.el-table__body');
    const rowCount = await table.locator('tr').count();
    if (rowCount > 0) {
      const productCell = table.locator('tr').first().locator('td').nth(1);
      const text = await productCell.textContent();
      expect(text).toMatch(/月卡|季卡|年卡/);
    }
  });

  test('should display payment method labels', async ({ page }) => {
    await page.waitForTimeout(2000);
    const table = page.locator('.el-table__body');
    const rowCount = await table.locator('tr').count();
    if (rowCount > 0) {
      const paymentCell = table.locator('tr').first().locator('td').nth(3);
      const text = await paymentCell.textContent();
      expect(text).toMatch(/支付宝|微信支付/);
    }
  });

  test('should display status tags', async ({ page }) => {
    await page.waitForTimeout(2000);
    const table = page.locator('.el-table__body');
    const rowCount = await table.locator('tr').count();
    if (rowCount > 0) {
      const statusTag = table.locator('tr').first().locator('.el-tag');
      await expect(statusTag).toBeVisible();
    }
  });

  test('should display amount with currency symbol', async ({ page }) => {
    await page.waitForTimeout(2000);
    const table = page.locator('.el-table__body');
    const rowCount = await table.locator('tr').count();
    if (rowCount > 0) {
      const amountCell = table.locator('tr').first().locator('td').nth(2);
      const text = await amountCell.textContent();
      expect(text).toContain('¥');
    }
  });
});
