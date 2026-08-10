/**
 * smoke.test.ts — T101 Vitest smoke
 *
 * 阶段一前端测试基础设施 sanity check：
 * - happy: Node fs / path 模块能 import + 设计文档可达
 * - edge: 解析失败时给出可读错误而非静默通过
 * - error: DESIGN.md 的 spacing tokens 全是 4 的倍数（防止 token 漂移）
 *
 * 不依赖 @vue/test-utils / happy-dom（避免 Vue 编译路径上的 type 噪音）。
 * SPEC: docs/superpowers/specs/2026-08-10-vitest-smoke-design.md
 */

import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

// T101 spec §AC-3.3: 从项目根 DESIGN.md 读 spacing tokens，断言全 4 的倍数
function readSpacingTokens(): Record<string, number> {
  // tests/unit → tests → web → app/web，需回退 3 层到项目根 (app/)
  // DESIGN.md 在项目根 (app/DESIGN.md), 因为仓库布局是 monorepo 风格
  const designPath = resolve(__dirname, '../../../../DESIGN.md')
  if (!existsSync(designPath)) {
    throw new Error(`DESIGN.md not found at ${designPath}`)
  }
  const content = readFileSync(designPath, 'utf-8')
  const fmMatch = content.match(/^```yaml\n([\s\S]*?)\n```/m)
  if (!fmMatch) {
    throw new Error('DESIGN.md must have YAML frontmatter block')
  }
  const block = fmMatch[1]
  const spacingMatch = block.match(/spacing:\n((?:  \w+:\s+\d+px\n?)+)/)
  if (!spacingMatch) {
    throw new Error('DESIGN.md must declare spacing tokens in frontmatter')
  }
  const tokens: Record<string, number> = {}
  for (const line of spacingMatch[1].trim().split('\n')) {
    const m = line.match(/^  (\w+):\s+(\d+)px$/)
    if (m) tokens[m[1]] = parseInt(m[2], 10)
  }
  return tokens
}

describe('T101 smoke test', () => {
  it('happy: project files exist (smoke check)', () => {
    // 不依赖具体模块，纯 sanity check：项目根目录可达
    const root = resolve(__dirname, '../..')
    expect(existsSync(resolve(root, 'package.json'))).toBe(true)
    expect(existsSync(resolve(root, 'nuxt.config.ts'))).toBe(true)
  })

  it('edge: DESIGN.md spacing tokens parse without throwing', () => {
    // 即便没有 spacing tokens（理论上不该发生），函数也得给可读错误
    // 这里用 try/catch 验证调用不静默失败
    let parsed: Record<string, number> | null = null
    let error: Error | null = null
    try {
      parsed = readSpacingTokens()
    } catch (e) {
      error = e as Error
    }
    expect(error, 'expected to parse DESIGN.md, got error: ' + (error?.message ?? '')).toBeNull()
    expect(parsed).not.toBeNull()
    expect(Object.keys(parsed!).length).toBeGreaterThan(0)
  })

  it('error: DESIGN.md spacing tokens are all multiples of 4 (DESIGN.md principle)', () => {
    const tokens = readSpacingTokens()
    expect(Object.keys(tokens).length).toBeGreaterThan(0)
    for (const [name, value] of Object.entries(tokens)) {
      expect(value % 4, `${name} = ${value}px must be multiple of 4 (DESIGN.md spacing principle)`).toBe(0)
    }
  })
})