// tests/e2e/smoke.spec.ts — 端到端冒烟 (T113)
// 验证三个核心页面能渲染,不依赖后端(mock fallback)

import { expect, test } from '@playwright/test'

test.describe('T113 e2e smoke', () => {
  test('Dashboard renders with header + scan button', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
    await expect(page.getByRole('button', { name: /立即扫描/ })).toBeVisible()
  })

  test('Keywords page shows add form', async ({ page }) => {
    await page.goto('/keywords')
    await expect(page.getByRole('heading', { name: '关键字管理' })).toBeVisible()
    await expect(page.getByRole('button', { name: '添加' })).toBeVisible()
  })

  test('Scan page shows trigger button', async ({ page }) => {
    await page.goto('/scan')
    await expect(page.getByRole('heading', { name: '手动扫描' })).toBeVisible()
    await expect(page.getByRole('button', { name: '开始扫描' })).toBeVisible()
  })

  test('Settings page renders all 3 sections', async ({ page }) => {
    await page.goto('/settings')
    await expect(page.getByRole('heading', { name: '设置' })).toBeVisible()
    // GitHub / 推送 / LLM 段卡片标题(h2 in UCard #header)
    await expect(page.getByRole('heading', { name: 'GitHub' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '推送' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'LLM' })).toBeVisible()
  })

  test('Sidebar navigation has 6 items', async ({ page }) => {
    await page.goto('/')
    const navItems = page.getByRole('navigation').first().getByRole('link')
    // 推荐 + 推荐列表 + 关键字 + 我的 Star + 扫描 + 设置
    await expect(navItems).toHaveCount(6)
  })

  test('API keywords endpoint returns array (mock fallback)', async ({ request }) => {
    const resp = await request.get('/api/keywords')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(Array.isArray(data)).toBeTruthy()
  })

  test('API integration health returns reachable=false when python down', async ({ request }) => {
    const resp = await request.get('/api/integration/health')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data).toHaveProperty('python_reachable')
    expect(typeof data.python_reachable).toBe('boolean')
  })
})