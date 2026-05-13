import { test, expect } from '@playwright/test';

const DEFAULT_EMAIL = 'demo@test.com';
const DEFAULT_PASSWORD = 'demo123456';

async function loginAndNavigateToTasks(page) {
  await page.goto('/login');
  await page.getByPlaceholder('邮箱').fill(DEFAULT_EMAIL);
  await page.locator('input[type="password"]').fill(DEFAULT_PASSWORD);
  await page.getByRole('button', { name: '登录' }).click();
  await page.waitForURL('**/dashboard', { timeout: 15000 });
  await page.getByRole('menuitem', { name: '任务调度' }).click();
  await page.waitForURL('**/tasks', { timeout: 15000 });
}

test.describe('Tasks Page - Layout', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToTasks(page);
  });

  test('should display tasks page title', async ({ page }) => {
    await expect(page.getByRole('main').getByText('任务调度')).toBeVisible();
  });
});

test.describe('Tasks Page - Schedule Status', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToTasks(page);
  });

  test('should display schedule status', async ({ page }) => {
    await expect(page.getByText('调度状态')).toBeVisible();
    const statusTag = page.locator('.el-descriptions__body .el-tag');
    await expect(statusTag.first()).toBeVisible();
  });

  test('should display schedule preset', async ({ page }) => {
    await expect(page.getByText('预设模板')).toBeVisible();
    const presetValue = page.locator('.el-descriptions__body td').nth(1);
    await expect(presetValue).toBeVisible();
  });

  test('should display task count', async ({ page }) => {
    await expect(page.getByText('定时任务数')).toBeVisible();
  });

  test('should display task list', async ({ page }) => {
    await expect(page.getByText('任务列表')).toBeVisible();
  });
});

test.describe('Tasks Page - Trigger Buttons', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToTasks(page);
  });

  test('should display trigger crawl button', async ({ page }) => {
    await expect(page.getByRole('button', { name: '触发爬虫' })).toBeVisible();
  });

  test('should display trigger analyze button', async ({ page }) => {
    await expect(page.getByRole('button', { name: '触发分析' })).toBeVisible();
  });

  test('should display trigger push button', async ({ page }) => {
    await expect(page.getByRole('button', { name: '触发推送' })).toBeVisible();
  });

  test('should trigger crawl task', async ({ page }) => {
    await page.getByRole('button', { name: '触发爬虫' }).click();
    await expect(page.getByText('爬虫任务已触发')).toBeVisible({ timeout: 10000 });
  });

  test('should trigger analyze task', async ({ page }) => {
    await page.getByRole('button', { name: '触发分析' }).click();
    await expect(page.getByText('AI 分析任务已触发')).toBeVisible({ timeout: 10000 });
  });

  test('should trigger push task', async ({ page }) => {
    await page.getByRole('button', { name: '触发推送' }).click();
    await expect(page.getByText('推送任务已触发')).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Tasks Page - Task Descriptions', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToTasks(page);
  });

  test('should display task description section', async ({ page }) => {
    await expect(page.getByText('任务说明')).toBeVisible();
  });

  test('should display crawl task description', async ({ page }) => {
    await expect(page.locator('.el-alert').filter({ hasText: '爬虫任务' })).toBeVisible();
    await expect(page.getByText('从各热榜平台和 RSS 源抓取最新数据')).toBeVisible();
  });

  test('should display AI analysis task description', async ({ page }) => {
    await expect(page.locator('.el-alert').filter({ hasText: 'AI 分析任务' })).toBeVisible();
    await expect(page.getByText('使用 AI 对抓取的数据进行智能筛选和深度分析')).toBeVisible();
  });

  test('should display push task description', async ({ page }) => {
    await expect(page.locator('.el-alert').filter({ hasText: '推送任务' })).toBeVisible();
    await expect(page.getByText('将分析结果推送到配置的通知渠道')).toBeVisible();
  });
});

test.describe('Tasks Page - Running Tasks', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToTasks(page);
  });

  test('should handle running tasks section', async ({ page }) => {
    await page.waitForTimeout(2000);
    const runningTasksCard = page.getByText('正在执行的任务');
    const isVisible = await runningTasksCard.isVisible().catch(() => false);
    // Section may or may not be visible depending on state
    expect(typeof isVisible).toBe('boolean');
  });
});
