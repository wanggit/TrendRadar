import { test, expect } from '@playwright/test';

const DEFAULT_EMAIL = 'demo@test.com';
const DEFAULT_PASSWORD = 'demo123456';

async function loginAndNavigateToConfig(page) {
  await page.goto('/login');
  await page.getByPlaceholder('邮箱').fill(DEFAULT_EMAIL);
  await page.locator('input[type="password"]').fill(DEFAULT_PASSWORD);
  await page.getByRole('button', { name: '登录' }).click();
  await page.waitForURL('**/dashboard', { timeout: 15000 });
  await page.getByRole('menuitem', { name: '配置管理' }).click();
  await page.waitForURL('**/config', { timeout: 15000 });
}

test.describe('Config Page - Navigation & Layout', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToConfig(page);
  });

  test('should display config sidebar with all modules', async ({ page }) => {
    await expect(page.getByText('配置中心')).toBeVisible();
    
    const modules = [
      '热榜平台', 'RSS 订阅', '报告模式', '筛选策略', 'AI 智能筛选',
      '推送内容控制', '推送通知', '调度设置', '调度时间线', '关键词',
      'AI 分析', 'AI 翻译', '高级设置'
    ];
    
    for (const mod of modules) {
      await expect(page.getByText(mod, { exact: true })).toBeVisible();
    }
  });

  test('should display sidebar action buttons', async ({ page }) => {
    await expect(page.getByRole('button', { name: '版本对比' })).toBeVisible();
    await expect(page.getByRole('button', { name: '导出配置' })).toBeVisible();
    await expect(page.getByRole('button', { name: '导入配置' })).toBeVisible();
  });

  test('should switch between config modules', async ({ page }) => {
    await page.getByText('RSS 订阅', { exact: true }).click();
    await expect(page.getByRole('heading', { name: 'RSS 订阅管理' })).toBeVisible();
    
    await page.getByText('报告模式', { exact: true }).click();
    await expect(page.getByRole('heading', { name: '报告模式' })).toBeVisible({ timeout: 10000 });
    
    await page.getByText('高级设置', { exact: true }).click();
    await expect(page.getByRole('heading', { name: '高级设置' })).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Config Page - 热榜平台 (Platforms)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToConfig(page);
  });

  test('should display platforms table', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '热榜平台配置' })).toBeVisible();
    await expect(page.getByRole('button', { name: '添加平台' })).toBeVisible();
  });

  test('should open add platform dialog', async ({ page }) => {
    await page.getByRole('button', { name: '添加平台' }).click();
    await expect(page.getByRole('heading', { name: '添加平台' })).toBeVisible();
    await expect(page.locator('.el-dialog')).toBeVisible();
  });

  test('should show preset platforms in dialog', async ({ page }) => {
    await page.getByRole('button', { name: '添加平台' }).click();
    await expect(page.getByText('微博热搜')).toBeVisible();
    await expect(page.getByText('百度热搜')).toBeVisible();
    await expect(page.getByText('知乎热榜')).toBeVisible();
  });

  test('should select and deselect preset platforms', async ({ page }) => {
    await page.getByRole('button', { name: '添加平台' }).click();
    
    await page.getByText('微博热搜').click();
    await expect(page.locator('.preset-item.selected').filter({ hasText: '微博热搜' })).toBeVisible();
    
    await page.getByText('微博热搜').click();
    await expect(page.locator('.preset-item.selected').filter({ hasText: '微博热搜' })).not.toBeVisible();
  });
});

test.describe('Config Page - RSS 订阅', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToConfig(page);
    await page.getByText('RSS 订阅', { exact: true }).click();
  });

  test('should display RSS management page', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'RSS 订阅管理' })).toBeVisible();
    await expect(page.getByRole('button', { name: '添加 RSS 源' })).toBeVisible();
  });

  test('should display global RSS settings', async ({ page }) => {
    await expect(page.getByText('启用 RSS 抓取')).toBeVisible();
    await expect(page.getByText('启用新鲜度过滤')).toBeVisible();
    await expect(page.getByText('最大文章年龄 (天)')).toBeVisible();
  });

  test('should open add RSS dialog', async ({ page }) => {
    await page.getByRole('button', { name: '添加 RSS 源' }).click();
    await expect(page.getByRole('heading', { name: '添加 RSS 源' })).toBeVisible();
    await expect(page.getByText('RSS 灵感库')).toBeVisible();
  });

  test('should show RSS inspiration sources', async ({ page }) => {
    await page.getByRole('button', { name: '添加 RSS 源' }).click();
    await expect(page.getByText('Bing 新闻')).toBeVisible();
    await expect(page.getByText('36氪')).toBeVisible();
    await expect(page.getByText('GitHub Trending')).toBeVisible();
  });

  test('should fill RSS form fields', async ({ page }) => {
    await page.getByRole('button', { name: '添加 RSS 源' }).click();
    
    await page.getByLabel('源 ID').fill('test-blog');
    await page.getByLabel('显示名称').fill('测试博客');
    await page.getByLabel('RSS URL').fill('https://example.com/feed.xml');
    
    await expect(page.getByLabel('源 ID')).toHaveValue('test-blog');
    await expect(page.getByLabel('显示名称')).toHaveValue('测试博客');
  });

  test('should click inspiration to fill URL', async ({ page }) => {
    await page.getByRole('button', { name: '添加 RSS 源' }).click();
    await page.getByText('科技/编程').click();
    await expect(page.getByLabel('RSS URL')).toHaveValue(/bing.com/);
  });
});

test.describe('Config Page - 报告模式 (Report)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToConfig(page);
    await page.getByText('报告模式', { exact: true }).click();
  });

  test('should display report mode settings', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '报告模式' })).toBeVisible();
    await expect(page.getByText('报告模式决定了推送内容的聚合方式')).toBeVisible();
  });

  test('should display all report mode options', async ({ page }) => {
    const select = page.locator('.el-form-item:has-text("报告模式") .el-select');
    await select.click();
    await page.waitForTimeout(500);
    
    await expect(page.locator('.el-select-dropdown__item', { hasText: 'current' })).toBeVisible();
    await expect(page.locator('.el-select-dropdown__item', { hasText: 'daily' })).toBeVisible();
    await expect(page.locator('.el-select-dropdown__item', { hasText: 'incremental' })).toBeVisible();
  });

  test('should display grouping options', async ({ page }) => {
    const select = page.locator('.el-form-item:has-text("分组维度") .el-select');
    await select.click();
    
    await expect(page.locator('.el-select-dropdown').getByText('keyword - 按关键词分组', { exact: true })).toBeVisible();
    await expect(page.locator('.el-select-dropdown').getByText('platform - 按平台分组', { exact: true })).toBeVisible();
  });

  test('should display numeric inputs', async ({ page }) => {
    await expect(page.getByText('排名高亮阈值')).toBeVisible();
    await expect(page.getByText('每关键词最大数量')).toBeVisible();
  });

  test('should have save and reset buttons', async ({ page }) => {
    await expect(page.getByRole('button', { name: '保存' })).toBeVisible();
    await expect(page.getByRole('button', { name: '重置' })).toBeVisible();
  });

  test('should change report mode', async ({ page }) => {
    const select = page.locator('.el-form-item:has-text("报告模式") .el-select');
    await select.click();
    await page.waitForTimeout(500);
    await page.locator('.el-select-dropdown__item', { hasText: 'daily' }).click();
    await expect(select).toContainText('daily');
  });
});

test.describe('Config Page - 筛选策略 (Filter)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToConfig(page);
    await page.getByText('筛选策略', { exact: true }).click();
  });

  test('should display filter settings', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '筛选策略' })).toBeVisible();
    await expect(page.getByText('筛选策略决定了如何从抓取的数据中过滤出你感兴趣的内容')).toBeVisible();
  });

  test('should display filter method options', async ({ page }) => {
    const select = page.locator('.el-form-item:has-text("筛选方法") .el-select');
    await select.click();
    
    await expect(page.locator('.el-select-dropdown').getByText('keyword - 关键词匹配')).toBeVisible();
    await expect(page.locator('.el-select-dropdown').getByText('ai - AI 智能筛选', { exact: true })).toBeVisible();
  });

  test('should show priority sort toggle when AI method selected', async ({ page }) => {
    const select = page.locator('.el-form-item:has-text("筛选方法") .el-select');
    await select.click();
    await page.locator('.el-select-dropdown').getByText('ai - AI 智能筛选', { exact: true }).click();
    
    await expect(page.getByText('按标签优先级排序')).toBeVisible();
  });
});

test.describe('Config Page - AI 智能筛选', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToConfig(page);
    await page.getByText('AI 智能筛选', { exact: true }).click();
  });

  test('should display AI filter settings', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'AI 智能筛选' })).toBeVisible();
    await expect(page.getByText('仅当筛选策略选择 AI 模式时生效')).toBeVisible();
  });

  test('should display all AI filter fields', async ({ page }) => {
    await expect(page.getByText('每批标题数量')).toBeVisible();
    await expect(page.getByText('分批间隔 (秒)')).toBeVisible();
    await expect(page.getByText('最低分数阈值')).toBeVisible();
    await expect(page.getByText('全量重分类阈值')).toBeVisible();
    await expect(page.getByText('兴趣描述', { exact: true })).toBeVisible();
    await expect(page.getByText('分类提示词', { exact: true })).toBeVisible();
    await expect(page.getByText('标签提取提示词', { exact: true })).toBeVisible();
    await expect(page.getByText('标签更新提示词', { exact: true })).toBeVisible();
  });

  test('should display text areas for prompts', async ({ page }) => {
    const textareas = page.locator('textarea');
    await expect(textareas).toHaveCount(4);
  });

  test('should display default content in interest description textarea', async ({ page }) => {
    const interestTextarea = page.getByRole('textbox', { name: '兴趣描述' });
    await expect(interestTextarea).toBeVisible();
    await expect(interestTextarea).toHaveValue(/下面是我要关注的内容/);
  });

  test('should display default content in classify prompt textarea', async ({ page }) => {
    const classifyTextarea = page.getByRole('textbox', { name: '分类提示词' });
    await expect(classifyTextarea).toBeVisible();
    await expect(classifyTextarea).toHaveValue(/\[system\]/);
  });

  test('should display default content in extract prompt textarea', async ({ page }) => {
    const extractTextarea = page.getByRole('textbox', { name: '标签提取提示词' });
    await expect(extractTextarea).toBeVisible();
    await expect(extractTextarea).toHaveValue(/\[system\]/);
  });

  test('should display default content in update tags prompt textarea', async ({ page }) => {
    const updateTextarea = page.getByRole('textbox', { name: '标签更新提示词' });
    await expect(updateTextarea).toBeVisible();
    await expect(updateTextarea).toHaveValue(/\[system\]/);
  });

  test('should edit interest description content', async ({ page }) => {
    const textarea = page.getByRole('textbox', { name: '兴趣描述' });
    await textarea.fill('1. 人工智能\n2. 机器学习');
    await expect(textarea).toHaveValue('1. 人工智能\n2. 机器学习');
  });

  test('should edit classify prompt content', async ({ page }) => {
    const textarea = page.getByRole('textbox', { name: '分类提示词' });
    await textarea.fill('[system]\n你是一个分类专家\n[user]\n请分类');
    await expect(textarea).toHaveValue('[system]\n你是一个分类专家\n[user]\n请分类');
  });

  test('should save AI filter configuration', async ({ page }) => {
    const interestTextarea = page.getByRole('textbox', { name: '兴趣描述' });
    await interestTextarea.fill('测试兴趣描述');
    
    await page.getByRole('button', { name: '保存' }).click();
    await expect(page.getByText('AI 智能筛选配置已保存')).toBeVisible();
  });

  test('should reset AI filter configuration', async ({ page }) => {
    const interestTextarea = page.getByRole('textbox', { name: '兴趣描述' });
    const originalValue = await interestTextarea.inputValue();
    
    await interestTextarea.fill('修改后的内容');
    await expect(interestTextarea).toHaveValue('修改后的内容');
    
    await page.getByRole('button', { name: '重置' }).click();
    await page.waitForTimeout(1000);
    await expect(page.getByText('已重置为上次保存的配置')).toBeVisible();
    // After reset, value should be different from '修改后的内容'
    await expect(interestTextarea).not.toHaveValue('修改后的内容');
  });
});

test.describe('Config Page - 推送内容控制 (Display)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToConfig(page);
    await page.getByText('推送内容控制', { exact: true }).click();
  });

  test('should display display settings', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '推送内容控制' })).toBeVisible();
  });

  test('should display region toggles', async ({ page }) => {
    await expect(page.getByText('区域开关与排序')).toBeVisible();
    await expect(page.getByText('推送区域')).toBeVisible();
    await expect(page.getByText('独立展示区配置')).toBeVisible();
  });

  test('should display standalone settings', async ({ page }) => {
    await expect(page.getByText('独立展示区配置')).toBeVisible();
    await expect(page.getByText('每源最多展示')).toBeVisible();
    await expect(page.getByText('展示的热榜平台')).toBeVisible();
    await expect(page.getByText('展示的 RSS 源')).toBeVisible();
  });
});

test.describe('Config Page - 推送通知 (Notification)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToConfig(page);
    await page.getByText('推送通知', { exact: true }).click();
  });

  test('should display notification settings', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '推送通知' })).toBeVisible();
    await expect(page.getByText('推送时间由调度设置控制')).toBeVisible();
  });

  test('should display all notification channels', async ({ page }) => {
    const channels = ['Telegram', '企业微信', '飞书', '钉钉', 'Bark', 'ntfy', 'Slack', '邮件', '通用 Webhook'];
    for (const ch of channels) {
      await expect(page.locator('.channel-name', { hasText: ch })).toBeVisible();
    }
  });

  test('should expand channel fields when enabled', async ({ page }) => {
    const telegramCheckbox = page.locator('.channel-card:has-text("Telegram") .el-checkbox');
    await telegramCheckbox.click();
    
    await expect(page.getByText('Bot Token')).toBeVisible();
    await expect(page.getByText('Chat ID')).toBeVisible();
  });

  test('should fill channel configuration', async ({ page }) => {
    const telegramCheckbox = page.locator('.channel-card:has-text("Telegram") .el-checkbox');
    await telegramCheckbox.click();
    
    const botTokenInput = page.locator('.channel-card:has-text("Telegram")').getByRole('textbox').first();
    await botTokenInput.fill('test-bot-token');
    await expect(botTokenInput).toHaveValue('test-bot-token');
  });
});

test.describe('Config Page - 调度设置 (Schedule)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToConfig(page);
    await page.getByText('调度设置', { exact: true }).click();
  });

  test('should display schedule settings', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '调度设置' })).toBeVisible();
    await expect(page.getByText('调度设置控制采集、分析、推送的执行时间和频率')).toBeVisible();
  });

  test('should display preset templates', async ({ page }) => {
    const select = page.locator('.el-form-item:has-text("预设模板") .el-select');
    await select.click();
    await page.waitForTimeout(500);
    
    await expect(page.locator('.el-select-dropdown__item', { hasText: '早晚汇总' })).toBeVisible();
    await expect(page.locator('.el-select-dropdown__item', { hasText: '全天候' })).toBeVisible();
    await expect(page.locator('.el-select-dropdown__item', { hasText: '办公时间' })).toBeVisible();
    await expect(page.locator('.el-select-dropdown__item', { hasText: '夜猫子' })).toBeVisible();
  });

  test('should display schedule info', async ({ page }) => {
    await expect(page.getByText('当前预设')).toBeVisible();
    await expect(page.getByText('调度状态')).toBeVisible();
  });

  test('should change schedule preset', async ({ page }) => {
    const select = page.locator('.el-form-item:has-text("预设模板") .el-select');
    await select.click();
    await page.waitForTimeout(500);
    await page.locator('.el-select-dropdown__item', { hasText: '全天候' }).click();
    await expect(select).toContainText('全天候');
  });
});

test.describe('Config Page - 调度时间线 (Timeline)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToConfig(page);
    await page.getByText('调度时间线', { exact: true }).click();
  });

  test('should display timeline page', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '调度时间线' })).toBeVisible();
    await expect(page.getByRole('button', { name: '加载预设' })).toBeVisible();
    await expect(page.getByRole('button', { name: '新建调度模式' })).toBeVisible();
  });

  test('should display active preset card', async ({ page }) => {
    await expect(page.getByText('当前调度模式')).toBeVisible();
  });

  test('should display preset templates list', async ({ page }) => {
    await expect(page.locator('.section-title', { hasText: '预设模板' })).toBeVisible();
    await expect(page.locator('.preset-card-name', { hasText: '早晚汇总' })).toBeVisible();
    await expect(page.locator('.preset-card-name', { hasText: '全天候' })).toBeVisible();
  });

  test('should select a preset template', async ({ page }) => {
    const presetCard = page.locator('.preset-card:has-text("全天候")');
    await presetCard.click();
    await expect(presetCard).toHaveClass(/active/);
  });

  test('should open new preset dialog', async ({ page }) => {
    await page.getByRole('button', { name: '新建调度模式' }).click();
    await expect(page.getByRole('heading', { name: '新建调度模式' })).toBeVisible();
    await expect(page.getByLabel('模式标识')).toBeVisible();
    await expect(page.getByLabel('显示名称')).toBeVisible();
  });

  test('should fill new preset form', async ({ page }) => {
    await page.getByRole('button', { name: '新建调度模式' }).click();
    await page.getByLabel('模式标识').fill('my_custom_schedule');
    await page.getByLabel('显示名称').fill('我的调度');
    await expect(page.getByLabel('模式标识')).toHaveValue('my_custom_schedule');
  });
});

test.describe('Config Page - 关键词 (Keywords)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToConfig(page);
    await page.getByText('关键词', { exact: true }).click();
  });

  test('should display keywords editor', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '关注关键词' })).toBeVisible();
    await expect(page.getByRole('button', { name: '保存' })).toBeVisible();
  });

  test('should display keyword syntax hints', async ({ page }) => {
    await expect(page.getByText('普通关键词')).toBeVisible();
    await expect(page.getByText('正则: /AI|人工智能/')).toBeVisible();
    await expect(page.getByText('别名: 胖东来 => 胖东来集团')).toBeVisible();
    await expect(page.getByText('排除: !广告')).toBeVisible();
    await expect(page.getByText('必须: +必须词')).toBeVisible();
  });

  test('should display keyword textarea', async ({ page }) => {
    await expect(page.locator('textarea')).toBeVisible();
  });

  test('should edit keywords', async ({ page }) => {
    const textarea = page.locator('textarea');
    await textarea.fill('人工智能\n/大模型|\n!广告');
    await expect(textarea).toHaveValue('人工智能\n/大模型|\n!广告');
  });

  test('should display word count', async ({ page }) => {
    await expect(page.locator('.word-count')).toBeVisible();
  });
});

test.describe('Config Page - AI 分析', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToConfig(page);
    await page.getByText('AI 分析', { exact: true }).click();
  });

  test('should display AI analysis settings', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'AI 分析功能' })).toBeVisible();
  });

  test('should display all AI analysis fields', async ({ page }) => {
    await expect(page.getByText('开启 AI 分析')).toBeVisible();
    await expect(page.getByText('输出语言', { exact: true })).toBeVisible();
    await expect(page.getByText('分析模式')).toBeVisible();
    await expect(page.getByText('最大分析条数')).toBeVisible();
    await expect(page.getByText('提示词内容')).toBeVisible();
  });

  test('should display data source toggles', async ({ page }) => {
    await expect(page.getByText('分析数据源')).toBeVisible();
    await expect(page.getByText('包含 RSS 内容')).toBeVisible();
    await expect(page.getByText('包含独立展示区')).toBeVisible();
    await expect(page.getByText('传递完整排名时间线')).toBeVisible();
  });

  test('should change analysis mode', async ({ page }) => {
    const select = page.locator('.el-form-item:has-text("分析模式") .el-select');
    await select.click();
    await expect(page.locator('.el-select-dropdown').getByText('follow_report - 跟随报告模式')).toBeVisible();
    await expect(page.locator('.el-select-dropdown').getByText('daily - 每日分析')).toBeVisible();
  });
});

test.describe('Config Page - AI 翻译', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToConfig(page);
    await page.getByText('AI 翻译', { exact: true }).click();
  });

  test('should display AI translation settings', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'AI 翻译功能' })).toBeVisible();
  });

  test('should display translation fields', async ({ page }) => {
    await expect(page.getByText('开启 AI 翻译')).toBeVisible();
    await expect(page.getByText('目标语言', { exact: true })).toBeVisible();
    await expect(page.getByText('提示词文件')).toBeVisible();
  });

  test('should display translation scope toggles', async ({ page }) => {
    await expect(page.getByText('翻译范围')).toBeVisible();
    await expect(page.getByText('热榜内容')).toBeVisible();
    await expect(page.getByText('RSS 内容')).toBeVisible();
    await expect(page.getByText('独立展示区')).toBeVisible();
  });

  test('should have three scope toggles', async ({ page }) => {
    const scopeSwitches = page.locator('.el-form-item:has-text("热榜内容") .el-switch, .el-form-item:has-text("RSS 内容") .el-switch, .el-form-item:has-text("独立展示区") .el-switch');
    await expect(scopeSwitches).toHaveCount(3);
  });
});

test.describe('Config Page - 高级设置 (Advanced)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToConfig(page);
    await page.getByText('高级设置', { exact: true }).click();
  });

  test('should display advanced settings', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '高级设置' })).toBeVisible();
    await expect(page.getByText('高级设置包含调试模式、爬虫参数和权重配置')).toBeVisible();
  });

  test('should display debug settings', async ({ page }) => {
    await expect(page.getByText('调试模式', { exact: true })).toBeVisible();
  });

  test('should display crawler settings', async ({ page }) => {
    await expect(page.getByText('请求间隔 (秒)')).toBeVisible();
    await expect(page.getByText('启用代理')).toBeVisible();
  });

  test('should display weight settings', async ({ page }) => {
    await expect(page.getByText('排名权重')).toBeVisible();
    await expect(page.getByText('关键词权重')).toBeVisible();
    await expect(page.getByText('热度权重')).toBeVisible();
  });

  test('should show proxy field when enabled', async ({ page }) => {
    const proxySwitch = page.locator('.el-form-item:has-text("启用代理") .el-switch');
    await proxySwitch.click();
    await expect(page.getByText('默认代理')).toBeVisible();
  });
});

test.describe('Config Page - Export/Import/Diff', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndNavigateToConfig(page);
  });

  test('should open version diff dialog', async ({ page }) => {
    await page.getByRole('button', { name: '版本对比' }).click();
    await expect(page.getByText('配置版本对比')).toBeVisible();
  });

  test('should display diff dialog content', async ({ page }) => {
    await page.getByRole('button', { name: '版本对比' }).click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    await expect(page.getByRole('button', { name: '关闭', exact: true })).toBeVisible();
  });

  test('should trigger import file dialog', async ({ page }) => {
    const importButton = page.getByRole('button', { name: '导入配置' });
    await expect(importButton).toBeVisible();
  });
});
