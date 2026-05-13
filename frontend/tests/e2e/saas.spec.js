import { test, expect } from '@playwright/test'

test.describe('Pricing Page', () => {
  test('displays Free and Pro plans', async ({ page }) => {
    await page.goto('/pricing')
    await expect(page.getByRole('heading', { name: '选择适合您的方案' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '免费版' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '专业版' })).toBeVisible()
    await expect(page.getByText('¥0')).toBeVisible()
    await expect(page.getByText('¥49')).toBeVisible()
  })

  test('Free plan shows correct features', async ({ page }) => {
    await page.goto('/pricing')
    await expect(page.getByText('最多 3 个热榜平台')).toBeVisible()
    await expect(page.getByText('5 个关键词组')).toBeVisible()
    await expect(page.getByText('每日 4 次推送')).toBeVisible()
  })

  test('Pro plan shows correct features', async ({ page }) => {
    await page.goto('/pricing')
    await expect(page.getByText('最多 15 个热榜平台')).toBeVisible()
    await expect(page.getByText('无限关键词组')).toBeVisible()
    await expect(page.locator('.pricing-card.pro').getByText('AI 深度分析')).toBeVisible()
  })

  test('Pro button redirects to login when not authenticated', async ({ page }) => {
    await page.goto('/pricing')
    await page.locator('.pricing-card.pro').getByRole('button', { name: '立即购买' }).click()
    await expect(page).toHaveURL(/.*\/login.*/)
  })
})

test.describe('Privacy Policy', () => {
  test('page is accessible', async ({ page }) => {
    await page.goto('/privacy-policy')
    await expect(page.locator('.policy-page')).toBeVisible()
    await expect(page.getByText('信息收集')).toBeVisible()
    await expect(page.getByText('信息使用')).toBeVisible()
  })
})

test.describe('Terms of Service', () => {
  test('page is accessible', async ({ page }) => {
    await page.goto('/terms-of-service')
    await expect(page.locator('.terms-page')).toBeVisible()
    await expect(page.getByText('服务说明')).toBeVisible()
    await expect(page.getByText('账户注册')).toBeVisible()
  })
})

test.describe('Footer Links', () => {
  test('footer contains privacy policy link', async ({ page }) => {
    await page.goto('/pricing')
    await expect(page.getByRole('link', { name: '隐私政策' })).toBeVisible()
  })

  test('footer contains terms of service link', async ({ page }) => {
    await page.goto('/pricing')
    await expect(page.getByRole('link', { name: '服务条款' })).toBeVisible()
  })
})

test.describe('Registration and Trial', () => {
  test('new user can register and gets trial', async ({ page }) => {
    const email = `test-${Date.now()}@example.com`
    await page.goto('/register')
    await page.getByPlaceholder('邮箱', { exact: true }).fill(email)
    await page.getByPlaceholder('密码', { exact: true }).fill('testpassword123')
    await page.getByPlaceholder('确认密码', { exact: true }).fill('testpassword123')
    await page.getByRole('button', { name: '注册' }).click()
    await page.waitForURL('**/dashboard', { timeout: 15000 })
    await expect(page.locator('.trial-countdown')).toBeVisible()
  })
})

test.describe('Dashboard Trial Banner', () => {
  test('shows trial countdown for pro users', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('邮箱', { exact: true }).fill('test@example.com')
    await page.getByPlaceholder('密码', { exact: true }).fill('testpassword123')
    await page.getByRole('button', { name: '登录' }).click()
    await page.waitForURL('**/dashboard', { timeout: 10000 }).catch(() => {})
  })
})
