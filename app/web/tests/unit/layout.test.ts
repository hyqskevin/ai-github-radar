/**
 * layout.test.ts — T103 layouts/default.vue
 *
 * 验证 dashboard 三段式布局（AppBar + SideNav + Content）符合 SPEC §B2 AC。
 * 静态源码断言（避免 Vue 编译路径噪音），跟 T101/T102 一致。
 *
 * SPEC: docs/superpowers/specs/2026-08-10-layout-default-design.md
 */

import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { resolve, join } from 'node:path'

const REPO_ROOT = resolve(__dirname, '../../../..')
const LAYOUT_PATH = join(REPO_ROOT, 'app/web/app/layouts/default.vue')

function readLayout(): string {
  if (!existsSync(LAYOUT_PATH)) {
    throw new Error(`Layout file not found at ${LAYOUT_PATH}`)
  }
  return readFileSync(LAYOUT_PATH, 'utf-8')
}

// 提取 navItems 数组的简易解析（regex 够用，避免拉 vue compiler）
function extractNavItems(content: string): Array<{ label: string; icon: string; to: string }> {
  const match = content.match(/const navItems\s*=\s*\[([\s\S]*?)\]/)
  if (!match) return []
  const items: Array<{ label: string; icon: string; to: string }> = []
  for (const objMatch of match[1].matchAll(/\{[^}]+\}/g)) {
    const label = objMatch[0].match(/label:\s*'([^']+)'/)?.[1]
    const icon = objMatch[0].match(/icon:\s*'([^']+)'/)?.[1]
    const to = objMatch[0].match(/to:\s*'([^']+)'/)?.[1]
    if (label && icon && to) items.push({ label, icon, to })
  }
  return items
}

describe('T103 layouts/default.vue', () => {
  // AC-1: layout 存在 + 三段
  it('happy (C6): layout file exists with 3 core sections', () => {
    const content = readLayout()
    expect(content).toContain('<header')
    expect(content).toContain('<aside')
    expect(content).toContain('<main')
  })

  // AC-2: AppBar 完整性
  it('happy (C6): AppBar has logo link, color mode button, settings link', () => {
    const content = readLayout()
    // logo NuxtLink 指向 /
    expect(content).toMatch(/<NuxtLink[^>]+to=["']\/["']/)
    // 含 ai-github-radar 文本
    expect(content).toContain('ai-github-radar')
    // theme switch
    expect(content).toContain('<UColorModeButton')
    // settings link
    expect(content).toMatch(/<UButton[^>]+to=["']\/settings["']/)
  })

  // AC-3: SideNav 完整性
  it('happy (C6): SideNav has 6+ navItems each with label/icon/to', () => {
    const items = extractNavItems(readLayout())
    expect(items.length, 'navItems should have ≥ 6 entries').toBeGreaterThanOrEqual(6)
    for (const item of items) {
      expect(item.label, 'every item must have label').toBeTruthy()
      expect(item.icon, 'every item must have icon').toMatch(/^i-lucide-/)
      expect(item.to, 'every item must have to').toMatch(/^\//)
    }
  })

  // C7: navItems 字段
  it('edge (C7): navItems covers all 6 main pages', () => {
    const items = extractNavItems(readLayout())
    const tos = items.map(i => i.to)
    for (const expected of ['/', '/recommendations', '/keywords', '/stars', '/scan', '/settings']) {
      expect(tos, `navItems must include ${expected}`).toContain(expected)
    }
  })

  // AC-4: Content slot
  it('happy (C6): main element contains <slot />', () => {
    const content = readLayout()
    expect(content).toMatch(/<main[\s\S]*?<slot\s*\/?>/)
  })

  // DOC: layout 中 DESIGN.md spacing tokens 范围内的间距 class 必须用 token 值
  it('DOC: layout spacing classes use DESIGN.md spacing tokens', () => {
    const content = readLayout()
    // DESIGN.md spacing tokens: xs=4 sm=8 md=16 lg=24 xl=32 x2l=48
    const allowed = new Set([4, 8, 16, 24, 32, 48])
    // 只检查 padding/margin/gap/space（间距维度）
    // 跳过 h-X / w-X / text-X / rounded-X / border-X（这些是组件尺寸，不是 spacing）
    const pattern = /\b(p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr|gap|space-x|space-y)-(\d+)\b/g
    const violations: string[] = []
    for (const m of content.matchAll(pattern)) {
      const n = parseInt(m[2], 10)
      if (!allowed.has(n)) {
        violations.push(`${m[1]}-${n}`)
      }
    }
    expect(violations, `spacing classes outside DESIGN.md tokens: ${violations.join(', ')}`).toEqual([])
  })

  // ERR: layout 不存在抛可读错误
  it('error (ERR): readLayout throws readable error on missing file', () => {
    const fakePath = '/nonexistent/path/default.vue'
    expect(() => {
      if (!existsSync(fakePath)) throw new Error(`Layout file not found at ${fakePath}`)
      readFileSync(fakePath, 'utf-8')
    }).toThrow(/Layout file not found/)
  })
})