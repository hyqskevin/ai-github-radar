// tests/e2e/smoke.spec.ts — 端到端冒烟 (T113+T125)
// 验证三个核心页面能渲染,不依赖后端(mock fallback)

import { expect, test } from '@playwright/test'

test.describe('T113 e2e smoke', () => {
  test('Dashboard renders with header', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  })

  test('Keywords page shows add form', async ({ page }) => {
    await page.goto('/keywords')
    await expect(page.getByRole('heading', { name: '关键字管理' })).toBeVisible()
    await expect(page.getByRole('button', { name: '添加' })).toBeVisible()
  })

  test('Recommendations page renders title', async ({ page }) => {
    await page.goto('/recommendations')
    await expect(page.getByRole('heading', { name: '推荐列表' })).toBeVisible()
  })

  test('Tasks page renders title', async ({ page }) => {
    await page.goto('/tasks')
    await expect(page.getByRole('heading', { name: '任务监控' })).toBeVisible()
  })

  test('Scheduler page renders title', async ({ page }) => {
    await page.goto('/scheduler')
    await expect(page.getByRole('heading', { name: '定时任务' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '新建任务' })).toBeVisible()
  })

  test('Settings page renders LLM section', async ({ page }) => {
    await page.goto('/settings')
    await expect(page.getByRole('heading', { name: '设置' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'GitHub' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'LLM 关键字提取' })).toBeVisible()
  })

  test('Sidebar navigation has 7 items (Tasks/Scheduler 新增)', async ({ page }) => {
    await page.goto('/')
    const navItems = page.getByRole('navigation').first().getByRole('link')
    await expect(navItems).toHaveCount(7)
  })

  test('API keywords endpoint returns array (mock fallback)', async ({ request }) => {
    const resp = await request.get('/api/keywords')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data).toBeTruthy()
  })

  test('API stars endpoint returns stars array', async ({ request }) => {
    const resp = await request.get('/api/stars')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data).toHaveProperty('stars')
    expect(Array.isArray(data.stars)).toBe(true)
  })

  test('API schedules endpoint returns schedules array', async ({ request }) => {
    const resp = await request.get('/api/schedules')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data).toHaveProperty('schedules')
    expect(Array.isArray(data.schedules)).toBe(true)
  })

  test('API jobs endpoint returns jobs array', async ({ request }) => {
    const resp = await request.get('/api/jobs')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data).toHaveProperty('jobs')
    expect(Array.isArray(data.jobs)).toBe(true)
  })

  test('API settings/llm endpoint returns provider field', async ({ request }) => {
    const resp = await request.get('/api/settings/llm')
    expect(resp.ok()).toBeTruthy()
    const data = await resp.json()
    expect(data).toHaveProperty('provider')
  })
})