// T106-T110 page smoke tests — 用 fs 读 page 源文件 + 验证关键标识

import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function pageSource(filename: string): string {
  return readFileSync(
    resolve(__dirname, `../../app/pages/${filename}`),
    'utf-8'
  )
}

describe('T125 page: index (Dashboard)', () => {
  it('contains Dashboard header + 4 API fetches', () => {
    const src = pageSource('index.vue')
    expect(src).toContain('Dashboard')
    expect(src).toContain('/api/stars/stats')
    expect(src).toContain('/api/recommendations')
    expect(src).toContain('/api/keywords')
    expect(src).toContain('/api/jobs')
  })

  it('uses real backend (no mockRecommendations fallback)', () => {
    const src = pageSource('index.vue')
    expect(src).not.toContain('mockRecommendations')
  })
})

describe('T107 page: keywords', () => {
  it('contains 关键字管理 + 添加 form', () => {
    const src = pageSource('keywords.vue')
    expect(src).toContain('关键字管理')
    expect(src).toContain('添加')
    expect(src).toContain('UTable')
  })

  it('handles add / toggle / delete actions', () => {
    const src = pageSource('keywords.vue')
    expect(src).toContain('handleAdd')
    expect(src).toContain('handleToggle')
    expect(src).toContain('handleDelete')
  })
})

describe('T108 page: recommendations', () => {
  it('contains 推荐列表 + 列表渲染', () => {
    const src = pageSource('recommendations.vue')
    expect(src).toContain('推荐列表')
    expect(src).toContain('useFetch')
    expect(src).toContain('matched_keywords')
  })
})

describe('T125 page: scan removed', () => {
  // T125: /scan 页合并到 /tasks + /scheduler
  it('scan.vue file no longer exists', () => {
    const path = resolve(__dirname, '../../app/pages/scan.vue')
    expect(() => pageSource('scan.vue')).toThrow()  // readFileSync throws
  })
})

describe('T110 page: stars', () => {
  it('renders 总 Star + 语言分布 + topics', () => {
    const src = pageSource('stars.vue')
    expect(src).toContain('我的 Star')
    expect(src).toContain('total')
    expect(src).toContain('by_language')
    expect(src).toContain('top_topics')
  })
})

describe('T138 page: stars pagination', () => {
  it('uses UPagination and computes page count from total', () => {
    const src = pageSource('stars.vue')
    expect(src).toContain('UPagination')
    expect(src).toContain('total')
    expect(src).toContain('Math.ceil')
  })
  it('passes limit+offset to /api/stars fetch', () => {
    const src = pageSource('stars.vue')
    expect(src).toContain('/api/stars')
    expect(src).toMatch(/limit/)
    expect(src).toMatch(/offset/)
  })
})

describe('T125 page: settings', () => {
  it('renders 设置 + GitHub / LLM sections', async () => {
    const src = pageSource('settings.vue')
    expect(src).toContain('设置')
    expect(src).toContain('GitHub')
    expect(src).toContain('LLM')
    expect(src).toContain('OpenAI')
  })
  it('no longer has 推送 UI', async () => {
    const src = pageSource('settings.vue')
    expect(src).not.toContain('飞书')
    expect(src).not.toContain('SMTP')
  })
})

describe('T127 page: tasks (job monitor)', () => {
  it('renders 任务监控 + uses /api/jobs', async () => {
    const src = pageSource('tasks.vue')
    expect(src).toContain('任务监控')
    expect(src).toContain('/api/jobs')
    expect(src).toContain('自动 10s 刷新')
  })
})

describe('T128 page: scheduler', () => {
  it('renders 定时任务 + cron form', async () => {
    const src = pageSource('scheduler.vue')
    expect(src).toContain('定时任务')
    expect(src).toContain('/api/schedules')
    expect(src).toContain('cron')
  })
  it('has cron presets', async () => {
    const src = pageSource('scheduler.vue')
    expect(src).toContain('0 9 * * *')
    expect(src).toContain('presets')
  })
})

describe('T125 layout nav', () => {
  it('has 8 nav items (Tasks/Scheduler/init added)', async () => {
    const src = readFileSync(
      resolve(__dirname, '../../app/layouts/default.vue'),
      'utf-8'
    )
    for (const label of ['推荐', '推荐列表', '我的 Star', '关键字', '初始化', '任务监控', '定时任务', '设置']) {
      expect(src).toContain(label)
    }
  })
})


describe('T129 page: init (one-shot setup)', () => {
  it('renders form with github_user + github_token + no_llm toggle', () => {
    const src = pageSource('init.vue')
    expect(src).toContain('初始化')
    expect(src).toContain('GitHub username')
    expect(src).toContain('Personal Access Token')
    expect(src).toContain('noLlm')
  })
  it('triggers /api/stars/refresh on save', () => {
    const src = pageSource('init.vue')
    expect(src).toContain('/api/stars/refresh')
    expect(src).toContain('/api/settings/all')
    expect(src).toContain('pollJob')
  })
})


describe('T129 page: stars has pull button', () => {
  it('stars.vue has /api/stars/refresh trigger button', () => {
    const src = pageSource('stars.vue')
    expect(src).toContain('/api/stars/refresh')
    expect(src).toContain('拉取 Star')
  })
})

describe('T129 page: recommendations has scan button', () => {
  it('recommendations.vue has /api/scan/async trigger', () => {
    const src = pageSource('recommendations.vue')
    expect(src).toContain('/api/scan/async')
    expect(src).toContain('手动 Scan')
  })
})

describe('T103 layout', () => {
  it('uses UNavigationMenu (not deprecated UVerticalNavigation)', () => {
    const src = readFileSync(
      resolve(__dirname, '../../app/layouts/default.vue'),
      'utf-8'
    )
    expect(src).toContain('UNavigationMenu')
    expect(src).not.toContain('UVerticalNavigation')
  })

  it('declares all 7 nav items (T125)', () => {
    const src = readFileSync(
      resolve(__dirname, '../../app/layouts/default.vue'),
      'utf-8'
    )
    for (const label of ['推荐', '推荐列表', '我的 Star', '关键字', '任务监控', '定时任务', '设置']) {
      expect(src).toContain(label)
    }
  })
})