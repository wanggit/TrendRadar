import { test, expect } from '@playwright/test';

const DEFAULT_EMAIL = 'demo@test.com';
const DEFAULT_PASSWORD = 'demo123456';

async function loginAndNavigateToNews(page) {
  await page.goto('/login');
  await page.getByPlaceholder('邮箱').fill(DEFAULT_EMAIL);
  await page.locator('input[type="password"]').fill(DEFAULT_PASSWORD);
  await page.getByRole('button', { name: '登录' }).click();
  await page.waitForURL('**/dashboard', { timeout: 15000 });
  await page.getByRole('menuitem', { name: '新闻浏览' }).click();
  await page.waitForURL('**/news', { timeout: 15000 });
}

test.describe('News Page - Layout & Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToNews(page);
  });

  test('should display news page title', async ({ page }) => {
    await expect(page.getByRole('main').getByText('新闻浏览')).toBeVisible();
  });

  test('should display tab navigation', async ({ page }) => {
    await expect(page.getByText('平台热榜')).toBeVisible();
    await expect(page.getByText('RSS 订阅')).toBeVisible();
  });

  test('should default to platform tab', async ({ page }) => {
    const platformTab = page.locator('.el-tab-pane[name="platform"]');
    await expect(page.locator('.el-tabs__item.is-active')).toContainText('平台热榜');
  });
});

test.describe('News Page - Platform Hot Lists', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToNews(page);
  });

  test('should display platform news table', async ({ page }) => {
    await expect(page.locator('.el-table')).toBeVisible();
  });

  test('should display table columns', async ({ page }) => {
    await expect(page.getByText('标题')).toBeVisible();
    await expect(page.getByText('排名')).toBeVisible();
    await expect(page.locator('.el-table__header').getByText('平台')).toBeVisible();
    await expect(page.locator('.el-table__header').getByText('抓取时间')).toBeVisible();
    await expect(page.locator('.el-table__header').getByText('操作')).toBeVisible();
  });

  test('should display search input', async ({ page }) => {
    await expect(page.getByPlaceholder('搜索关键词')).toBeVisible();
  });

  test('should display platform filter dropdown', async ({ page }) => {
    const platformSelect = page.locator('.el-select').first();
    await expect(platformSelect).toBeVisible();
  });

  test('should display search button', async ({ page }) => {
    await expect(page.getByRole('button', { name: '搜索' })).toBeVisible();
  });

  test('should search by keyword', async ({ page }) => {
    await page.getByPlaceholder('搜索关键词').fill('AI');
    await page.getByRole('button', { name: '搜索' }).click();
    await page.waitForTimeout(1500);
    await expect(page.locator('.el-table')).toBeVisible();
  });

  test('should display pagination', async ({ page }) => {
    await expect(page.locator('.el-pagination')).toBeVisible();
  });

  test('should show view link for each news item', async ({ page }) => {
    await page.waitForTimeout(2000);
    const viewLinks = page.locator('.el-table__body tr .el-link');
    const count = await viewLinks.count();
    if (count > 0) {
      await expect(viewLinks.first()).toBeVisible();
      await expect(viewLinks.first()).toContainText('查看');
    }
  });
});

test.describe('News Page - RSS Tab', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToNews(page);
  });

  test('should switch to RSS tab', async ({ page }) => {
    await page.getByText('RSS 订阅').click();
    await page.waitForTimeout(1000);
    await expect(page.locator('.el-tabs__item.is-active')).toContainText('RSS 订阅');
  });

  test('should display RSS items table after switching', async ({ page }) => {
    await page.getByText('RSS 订阅').click();
    await page.waitForTimeout(2000);
    await expect(page.locator('.el-table')).toBeVisible();
  });

  test('should display RSS table columns', async ({ page }) => {
    await page.getByText('RSS 订阅').click();
    await page.waitForTimeout(2000);
    await expect(page.getByText('标题')).toBeVisible();
    await expect(page.getByText('来源')).toBeVisible();
    await expect(page.getByText('发布时间')).toBeVisible();
    await expect(page.getByText('操作')).toBeVisible();
  });

  test('should display RSS search input', async ({ page }) => {
    await page.getByText('RSS 订阅').click();
    await page.waitForTimeout(1000);
    await expect(page.getByPlaceholder('搜索关键词')).toBeVisible();
  });

  test('should display RSS feed filter dropdown', async ({ page }) => {
    await page.getByText('RSS 订阅').click();
    await page.waitForTimeout(1000);
    await expect(page.locator('.el-select').first()).toBeVisible();
  });

  test('should display RSS pagination', async ({ page }) => {
    await page.getByText('RSS 订阅').click();
    await page.waitForTimeout(2000);
    await expect(page.locator('.el-pagination')).toBeVisible();
  });
});
