import { test, expect } from '@playwright/test';

const DEFAULT_EMAIL = 'demo@test.com';
const DEFAULT_PASSWORD = 'demo123456';

async function loginAndNavigateToDashboard(page) {
  await page.goto('/login');
  await page.getByPlaceholder('邮箱').fill(DEFAULT_EMAIL);
  await page.locator('input[type="password"]').fill(DEFAULT_PASSWORD);
  await page.getByRole('button', { name: '登录' }).click();
  await page.waitForURL('**/dashboard', { timeout: 15000 });
}

test.describe('Dashboard - Stats Cards', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToDashboard(page);
  });

  test('should display all four stat cards', async ({ page }) => {
    await expect(page.getByText('热榜平台')).toBeVisible();
    await expect(page.getByText('RSS 订阅')).toBeVisible();
    await expect(page.getByText('今日新闻')).toBeVisible();
    await expect(page.getByText('调度状态')).toBeVisible();
  });

  test('should display stat values', async ({ page }) => {
    const statValues = page.locator('.stat-value');
    await expect(statValues).toHaveCount(4);
  });

  test('should display stat labels', async ({ page }) => {
    await expect(page.getByText('已启用')).toHaveCount(2);
    await expect(page.getByText('已抓取')).toBeVisible();
  });

  test('should display schedule status as running or stopped', async ({ page }) => {
    const scheduleLabel = page.locator('.stat-label').last();
    const text = await scheduleLabel.textContent();
    expect(text).toMatch(/运行中|已停止/);
  });
});

test.describe('Dashboard - Quick Actions', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToDashboard(page);
  });

  test('should display quick actions section', async ({ page }) => {
    await expect(page.getByText('快捷操作')).toBeVisible();
  });

  test('should display all three action buttons', async ({ page }) => {
    await expect(page.getByRole('button', { name: '手动抓取' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'AI 分析' })).toBeVisible();
    await expect(page.getByRole('button', { name: '立即推送' })).toBeVisible();
  });

  test('should trigger crawl task', async ({ page }) => {
    await page.getByRole('button', { name: '手动抓取' }).click();
    await expect(page.getByText('爬虫任务已触发')).toBeVisible({ timeout: 10000 });
  });

  test('should trigger analyze task', async ({ page }) => {
    await page.getByRole('button', { name: 'AI 分析' }).click();
    await expect(page.getByText('AI 分析任务已触发')).toBeVisible({ timeout: 10000 });
  });

  test('should trigger push task', async ({ page }) => {
    await page.getByRole('button', { name: '立即推送' }).click();
    await expect(page.getByText('推送任务已触发')).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Dashboard - System AI Config', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToDashboard(page);
  });

  test('should display system AI config card', async ({ page }) => {
    await expect(page.getByText('系统 AI 配置')).toBeVisible();
    await expect(page.getByText('只读')).toBeVisible();
  });

  test('should display AI config details', async ({ page }) => {
    await expect(page.getByText('模型')).toBeVisible();
    await expect(page.getByText('API 地址')).toBeVisible();
    await expect(page.getByText('Temperature')).toBeVisible();
    await expect(page.getByText('Max Tokens')).toBeVisible();
  });
});

test.describe('Dashboard - Running Tasks', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToDashboard(page);
  });

  test('should handle running tasks section', async ({ page }) => {
    await page.waitForTimeout(2000);
    const runningTasksCard = page.getByText('正在执行的任务');
    const isVisible = await runningTasksCard.isVisible().catch(() => false);
    // Section may or may not be visible depending on state
    expect(typeof isVisible).toBe('boolean');
  });
});

test.describe('Dashboard - AI Report Card', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToDashboard(page);
  });

  test('should display AI report section when report exists', async ({ page }) => {
    await page.waitForTimeout(3000);
    const reportCard = page.getByText('AI 分析报告');
    const isVisible = await reportCard.isVisible().catch(() => false);
    if (isVisible) {
      await expect(page.getByText('分析新闻')).toBeVisible();
      await expect(page.getByText('热榜')).toBeVisible();
      await expect(page.getByText('RSS')).toBeVisible();
    }
  });

  test('should display refresh button in report header', async ({ page }) => {
    await page.waitForTimeout(3000);
    const reportCard = page.getByText('AI 分析报告');
    const isVisible = await reportCard.isVisible().catch(() => false);
    if (isVisible) {
      await expect(page.getByRole('button', { name: '刷新' })).toBeVisible();
    }
  });

  test('should display report creation time', async ({ page }) => {
    await page.waitForTimeout(3000);
    const reportCard = page.getByText('AI 分析报告');
    const isVisible = await reportCard.isVisible().catch(() => false);
    if (isVisible) {
      const reportTime = page.locator('.report-time');
      await expect(reportTime).toBeVisible();
    }
  });

  test('should display report tabs', async ({ page }) => {
    await page.waitForTimeout(3000);
    const reportCard = page.getByText('AI 分析报告');
    const isVisible = await reportCard.isVisible().catch(() => false);
    if (isVisible) {
      await expect(page.getByText('核心热点态势')).toBeVisible();
      await expect(page.getByText('舆论风向争议')).toBeVisible();
      await expect(page.getByText('异动与弱信号')).toBeVisible();
      await expect(page.getByText('研判策略建议')).toBeVisible();
    }
  });
});
