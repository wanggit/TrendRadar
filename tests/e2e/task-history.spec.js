import { test, expect } from '@playwright/test';

const DEFAULT_EMAIL = 'demo@test.com';
const DEFAULT_PASSWORD = 'demo123456';

async function loginAndNavigateToTaskHistory(page) {
  await page.goto('/login');
  await page.getByPlaceholder('邮箱').fill(DEFAULT_EMAIL);
  await page.locator('input[type="password"]').fill(DEFAULT_PASSWORD);
  await page.getByRole('button', { name: '登录' }).click();
  await page.waitForURL('**/dashboard', { timeout: 15000 });
  await page.getByRole('menuitem', { name: '任务历史' }).click();
  await page.waitForURL('**/task-history', { timeout: 15000 });
}

test.describe('Task History - Layout', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToTaskHistory(page);
  });

  test('should display task history page title', async ({ page }) => {
    await expect(page.getByText('任务执行历史')).toBeVisible();
  });

  test('should display refresh button', async ({ page }) => {
    await expect(page.getByRole('button', { name: '刷新' })).toBeVisible();
  });
});

test.describe('Task History - Filters', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToTaskHistory(page);
  });

  test('should display task type filter', async ({ page }) => {
    const taskTypeSelect = page.locator('.el-select').first();
    await expect(taskTypeSelect).toBeVisible();
  });

  test('should display task type options', async ({ page }) => {
    const taskTypeSelect = page.locator('.el-select').first();
    await taskTypeSelect.click();
    await page.waitForTimeout(500);

    await expect(page.getByRole('option', { name: '全部' }).first()).toBeVisible();
    await expect(page.getByRole('option', { name: '平台抓取' }).first()).toBeVisible();
    await expect(page.getByRole('option', { name: 'AI 分析' }).first()).toBeVisible();
    await expect(page.getByRole('option', { name: '推送通知' }).first()).toBeVisible();
    await page.keyboard.press('Escape');
  });

  test('should display status filter', async ({ page }) => {
    const statusSelect = page.locator('.el-select').nth(1);
    await expect(statusSelect).toBeVisible();
  });

  test('should display status options', async ({ page }) => {
    const statusSelect = page.locator('.el-select').nth(1);
    await statusSelect.click();
    await page.waitForTimeout(500);

    await expect(page.getByRole('option', { name: '全部' }).first()).toBeVisible();
    await expect(page.getByRole('option', { name: '成功' }).first()).toBeVisible();
    await expect(page.getByRole('option', { name: '失败' }).first()).toBeVisible();
    await expect(page.getByRole('option', { name: '运行中' }).first()).toBeVisible();
    await page.keyboard.press('Escape');
  });

  test('should filter by task type', async ({ page }) => {
    const taskTypeSelect = page.locator('.el-select').first();
    await taskTypeSelect.click();
    await page.waitForTimeout(500);
    await page.getByRole('option', { name: '平台抓取' }).first().click();
    await page.waitForTimeout(1500);
    await expect(page.locator('.el-table')).toBeVisible();
  });

  test('should filter by status', async ({ page }) => {
    const statusSelect = page.locator('.el-select').nth(1);
    await statusSelect.click();
    await page.waitForTimeout(500);
    await page.getByRole('option', { name: '成功' }).first().click();
    await page.waitForTimeout(1500);
    await expect(page.locator('.el-table')).toBeVisible();
  });
});

test.describe('Task History - Task Logs Table', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToTaskHistory(page);
  });

  test('should display task logs table', async ({ page }) => {
    await expect(page.locator('.el-table')).toBeVisible();
  });

  test('should display table columns', async ({ page }) => {
    await expect(page.locator('.el-table__header').getByText('任务')).toBeVisible();
    await expect(page.locator('.el-table__header').getByText('状态')).toBeVisible();
    await expect(page.locator('.el-table__header').getByText('进度')).toBeVisible();
    await expect(page.locator('.el-table__header').getByText('当前步骤')).toBeVisible();
    await expect(page.locator('.el-table__header').getByText('耗时')).toBeVisible();
    await expect(page.locator('.el-table__header').getByText('开始时间')).toBeVisible();
    await expect(page.locator('.el-table__header').getByText('操作')).toBeVisible();
  });

  test('should display detail button for each log entry', async ({ page }) => {
    await page.waitForTimeout(2000);
    const detailButtons = page.locator('.el-table__body tr .el-button--link');
    const count = await detailButtons.count();
    if (count > 0) {
      await expect(detailButtons.first()).toBeVisible();
      await expect(detailButtons.first()).toContainText('详情');
    }
  });
});

test.describe('Task History - Pagination', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToTaskHistory(page);
  });

  test('should display pagination', async ({ page }) => {
    await expect(page.locator('.el-pagination')).toBeVisible();
  });

  test('should display page size options', async ({ page }) => {
    await expect(page.locator('.el-pagination__sizes').getByText('20条/页')).toBeVisible();
  });

  test('should display total count', async ({ page }) => {
    await expect(page.locator('.el-pagination__total')).toBeVisible();
  });
});

test.describe('Task History - Log Detail Dialog', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToTaskHistory(page);
  });

  test('should open log detail dialog when clicking detail', async ({ page }) => {
    await page.waitForTimeout(2000);
    const detailButtons = page.locator('.el-table__body tr .el-button--link');
    const count = await detailButtons.count();
    if (count > 0) {
      await detailButtons.first().click();
      await expect(page.getByText('任务执行日志')).toBeVisible({ timeout: 5000 });
      await expect(page.locator('.el-dialog')).toBeVisible();
    }
  });

  test('should display log meta information in dialog', async ({ page }) => {
    await page.waitForTimeout(2000);
    const detailButtons = page.locator('.el-table__body tr .el-button--link');
    const count = await detailButtons.count();
    if (count > 0) {
      await detailButtons.first().click();
      await page.waitForTimeout(1000);
      await expect(page.getByText('任务')).toBeVisible();
      await expect(page.getByText('状态')).toBeVisible();
      await expect(page.getByText('开始时间')).toBeVisible();
      await expect(page.getByText('完成时间')).toBeVisible();
      await expect(page.getByText('耗时')).toBeVisible();
      await expect(page.getByText('进度')).toBeVisible();
    }
  });

  test('should display log entries section in dialog', async ({ page }) => {
    await page.waitForTimeout(2000);
    const detailButtons = page.locator('.el-table__body tr .el-button--link');
    const count = await detailButtons.count();
    if (count > 0) {
      await detailButtons.first().click();
      await page.waitForTimeout(1000);
      await expect(page.locator('.log-section')).toBeVisible();
    }
  });

  test('should show no logs message when no log entries', async ({ page }) => {
    await page.waitForTimeout(2000);
    const detailButtons = page.locator('.el-table__body tr .el-button--link');
    const count = await detailButtons.count();
    if (count > 0) {
      await detailButtons.first().click();
      await page.waitForTimeout(1000);
      const noLogs = page.locator('.no-logs');
      const isVisible = await noLogs.isVisible().catch(() => false);
      if (isVisible) {
        await expect(noLogs).toContainText('暂无日志记录');
      }
    }
  });
});

test.describe('Task History - Refresh', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToTaskHistory(page);
  });

  test('should refresh task logs', async ({ page }) => {
    await page.getByRole('button', { name: '刷新' }).click();
    await page.waitForTimeout(1500);
    await expect(page.locator('.el-table')).toBeVisible();
  });
});
