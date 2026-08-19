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

describe('T106 page: index (Dashboard)', () => {
  it('contains Dashboard header + scan button label', () => {
    const src = pageSource('index.vue')
    expect(src).toContain('Dashboard')
    expect(src).toContain('立即扫描')
  })

  it('uses mockRecommendations as fallback (阶段一)', () => {
    const src = pageSource('index.vue')
    expect(src).toContain('useKeywordsStore')
    expect(src).toContain('mockRecommendations')
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

describe('T109 page: scan', () => {
  it('contains 手动扫描 + triggerScan function', () => {
    const src = pageSource('scan.vue')
    expect(src).toContain('手动扫描')
    expect(src).toContain('triggerScan')
    expect(src).toContain('开始扫描')
  })

  it('POSTs /api/scan with push target', () => {
    const src = pageSource('scan.vue')
    expect(src).toContain('/api/scan')
    expect(src).toContain('push')
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

describe('T110 page: settings', () => {
  it('renders 设置 + GitHub / 推送 / LLM sections', () => {
    const src = pageSource('settings.vue')
    expect(src).toContain('设置')
    expect(src).toContain('GitHub')
    expect(src).toContain('推送')
    expect(src).toContain('LLM')
    expect(src).toContain('OpenAI')
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

  it('declares all 6 nav items', () => {
    const src = readFileSync(
      resolve(__dirname, '../../app/layouts/default.vue'),
      'utf-8'
    )
    for (const label of ['推荐', '推荐列表', '关键字', '我的 Star', '扫描', '设置']) {
      expect(src).toContain(label)
    }
  })
})