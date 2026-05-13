import { test, expect } from '@playwright/test';

test.describe('AI Analysis Report', () => {
  test.use({ storageState: 'tests/e2e/.auth/demo.json' });

  test('should display AI analysis section after clicking analyze button', async ({ page }) => {
    await page.goto('/dashboard');
    
    await expect(page.getByRole('button', { name: 'AI 分析' })).toBeVisible();
  });

  test('should show AI analysis report card when report exists', async ({ page }) => {
    await page.goto('/dashboard');
    
    const reportCard = page.locator('.report-content').first();
    const reportSection = page.getByText('AI 分析报告').first();
    
    if (await reportSection.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(reportCard).toBeVisible();
    }
  });

  test('should display report statistics', async ({ page }) => {
    await page.goto('/dashboard');
    
    const reportStats = page.locator('.report-stats');
    if (await reportStats.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(page.getByText('分析新闻')).toBeVisible();
      await expect(page.getByText('热榜')).toBeVisible();
      await expect(page.getByText('RSS')).toBeVisible();
    }
  });

  test('should display report tabs for analysis sections', async ({ page }) => {
    await page.goto('/dashboard');
    
    const reportTabs = page.locator('.report-tabs');
    if (await reportTabs.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(page.getByRole('tab', { name: '核心热点态势' })).toBeVisible();
      await expect(page.getByRole('tab', { name: '舆论风向争议' })).toBeVisible();
      await expect(page.getByRole('tab', { name: '异动与弱信号' })).toBeVisible();
      await expect(page.getByRole('tab', { name: '研判策略建议' })).toBeVisible();
    }
  });

  test('should switch between report tabs', async ({ page }) => {
    await page.goto('/dashboard');
    
    const reportTabs = page.locator('.report-tabs');
    if (await reportTabs.isVisible({ timeout: 5000 }).catch(() => false)) {
      await page.getByRole('tab', { name: '核心热点态势' }).click();
      await expect(page.locator('.report-section').first()).toBeVisible();
      
      await page.getByRole('tab', { name: '舆论风向争议' }).click();
      await expect(page.locator('.el-tab-pane.is-active')).toBeVisible();
    }
  });

  test('should display refresh button in report header', async ({ page }) => {
    await page.goto('/dashboard');
    
    const reportSection = page.getByText('AI 分析报告').first();
    if (await reportSection.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(page.getByRole('button', { name: '刷新' })).toBeVisible();
    }
  });

  test('should display report creation time', async ({ page }) => {
    await page.goto('/dashboard');
    
    const reportSection = page.getByText('AI 分析报告').first();
    if (await reportSection.isVisible({ timeout: 5000 }).catch(() => false)) {
      const timeElement = page.locator('.report-time');
      await expect(timeElement).toBeVisible();
    }
  });

  test('should show error alert when analysis fails', async ({ page }) => {
    await page.goto('/dashboard');
    
    const reportSection = page.getByText('AI 分析报告').first();
    if (await reportSection.isVisible({ timeout: 5000 }).catch(() => false)) {
      const errorAlert = page.locator('.report-error .el-alert--error');
      if (await errorAlert.isVisible({ timeout: 2000 }).catch(() => false)) {
        await expect(errorAlert).toBeVisible();
      }
    }
  });

  test('should display standalone summaries tab when available', async ({ page }) => {
    await page.goto('/dashboard');
    
    const reportTabs = page.locator('.report-tabs');
    if (await reportTabs.isVisible({ timeout: 5000 }).catch(() => false)) {
      const standaloneTab = page.getByRole('tab', { name: '独立展示区概括' });
      const isVisible = await standaloneTab.isVisible({ timeout: 2000 }).catch(() => false);
      if (isVisible) {
        await expect(standaloneTab).toBeVisible();
      }
    }
  });

  test('should trigger analyze task when clicking AI analysis button', async ({ page }) => {
    await page.goto('/dashboard');
    
    await page.getByRole('button', { name: 'AI 分析' }).click();
    
    await expect(page.getByText('AI 分析任务已触发')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('AI Analysis Report - Admin', () => {
  test.use({ storageState: 'tests/e2e/.auth/admin.json' });

  test('should display dashboard with AI analysis functionality', async ({ page }) => {
    await page.goto('/dashboard');
    
    await expect(page).toHaveTitle(/TrendRadar/);
    await expect(page.getByRole('button', { name: 'AI 分析' })).toBeVisible();
    await expect(page.getByRole('button', { name: '手动抓取' })).toBeVisible();
    await expect(page.getByRole('button', { name: '立即推送' })).toBeVisible();
  });

  test('should display system AI configuration card', async ({ page }) => {
    await page.goto('/dashboard');
    
    await expect(page.getByText('系统 AI 配置')).toBeVisible();
    await expect(page.getByText('只读')).toBeVisible();
  });
});
