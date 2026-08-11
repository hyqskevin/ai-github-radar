/**
 * handlers.ts — T105 handler 函数集合
 *
 * 把 Nitro handler 内的业务逻辑抽出来，便于 vitest 直接单测。
 * 端点文件（如 keywords.get.ts）只调这里，不带额外逻辑。
 *
 * SPEC: docs/superpowers/specs/2026-08-10-nitro-http-design.md
 */

import type { Keyword, Recommendation } from './types'

// 进程内存储（阶段一限制：重启清空）
const keywords = new Map<number, Keyword>()
const recommendations = new Map<number, Recommendation>()
let nextKeywordId = 1
let nextRecId = 1

// mock seed — 进程启动时插入
const SEED_KEYWORDS: Omit<Keyword, 'id'>[] = [
  { term: 'agent', weight: 1.5, source: 'auto', enabled: true },
  { term: 'claude code', weight: 2.0, source: 'manual', enabled: true },
  { term: 'mcp', weight: 1.2, source: 'auto', enabled: false },
  { term: 'rust', weight: 0.8, source: 'manual', enabled: true },
  { term: 'nuxt', weight: 1.0, source: 'auto', enabled: true },
  { term: 'typescript', weight: 1.3, source: 'manual', enabled: false }
]

let seeded = false
function ensureSeeded() {
  if (seeded) return
  for (const k of SEED_KEYWORDS) {
    const id = nextKeywordId++
    keywords.set(id, { id, ...k })
  }
  seeded = true
}

// 测试用：每次测试前重置
export function _resetStore() {
  keywords.clear()
  recommendations.clear()
  nextKeywordId = 1
  nextRecId = 1
  seeded = false
  ensureSeeded()
}

// -----------------------------------------------------------------------------
// Health
// -----------------------------------------------------------------------------

export function getHealth() {
  return {
    status: 'ok',
    service: 'ai-github-radar-web',
    timestamp: new Date().toISOString()
  }
}

// -----------------------------------------------------------------------------
// Keywords
// -----------------------------------------------------------------------------

export function listKeywords(filters: { source?: string; enabled?: boolean } = {}): Keyword[] {
  ensureSeeded()
  let items = Array.from(keywords.values())
  if (filters.source) items = items.filter(k => k.source === filters.source)
  if (filters.enabled !== undefined) items = items.filter(k => k.enabled === filters.enabled)
  return items
}

export class HttpError extends Error {
  constructor(public statusCode: number, message: string) {
    super(message)
    this.name = 'HttpError'
  }
}

export function createKeyword(input: { term?: string; weight?: number }): Keyword {
  ensureSeeded()
  if (typeof input.term !== 'string' || !input.term.trim()) {
    throw new HttpError(400, 'term is required and must be non-empty')
  }
  if (typeof input.weight !== 'number' || Number.isNaN(input.weight)) {
    throw new HttpError(400, 'weight must be a number')
  }
  const term = input.term.trim()
  if (Array.from(keywords.values()).some(k => k.term === term)) {
    throw new HttpError(409, `keyword "${term}" already exists`)
  }
  const id = nextKeywordId++
  const created: Keyword = {
    id,
    term,
    weight: input.weight,
    source: 'manual',  // POST 永远标记为 manual（auto 来源只有 init 流程）
    enabled: true
  }
  keywords.set(id, created)
  return created
}

export function updateKeyword(id: number, patch: Partial<Omit<Keyword, 'id'>>): Keyword {
  ensureSeeded()
  const existing = keywords.get(id)
  if (!existing) throw new HttpError(404, `keyword id=${id} not found`)
  // 拒绝改 source（auto 来源是只读的）
  if (patch.source !== undefined && patch.source !== existing.source) {
    throw new HttpError(400, 'cannot change source')
  }
  const updated: Keyword = { ...existing, ...patch, id }
  keywords.set(id, updated)
  return updated
}

export function deleteKeyword(id: number): void {
  ensureSeeded()
  if (!keywords.has(id)) throw new HttpError(404, `keyword id=${id} not found`)
  keywords.delete(id)
}

// -----------------------------------------------------------------------------
// Recommendations
// -----------------------------------------------------------------------------

export function listRecommendations(opts: { limit?: number; offset?: number } = {}): Recommendation[] {
  let items = Array.from(recommendations.values()).sort((a, b) => b.id - a.id)
  const offset = opts.offset ?? 0
  const limit = opts.limit ?? 50
  return items.slice(offset, offset + limit)
}

export function createRecommendation(input: Omit<Recommendation, 'id' | 'created_at'>): Recommendation {
  const id = nextRecId++
  const rec: Recommendation = {
    ...input,
    id,
    created_at: new Date().toISOString()
  }
  recommendations.set(id, rec)
  return rec
}

// -----------------------------------------------------------------------------
// Scan (mock — 真实扫描在 Python 后端，阶段二对接)
// -----------------------------------------------------------------------------

export function runScan(opts: { dryRun?: boolean } = {}): { status: string; matched: number; pushed: number } {
  ensureSeeded()
  const enabledKws = Array.from(keywords.values()).filter(k => k.enabled)
  // mock：随机生成 0-20 条匹配
  const matched = Math.floor(Math.random() * 20)
  const pushed = opts.dryRun ? 0 : matched
  return {
    status: 'ok',
    matched,
    pushed
  }
}

// -----------------------------------------------------------------------------
// Stars stats (mock — 真实数据从 Python 后端拉，阶段二对接)
// -----------------------------------------------------------------------------

export function getStarsStats() {
  // mock 统计 — 阶段二用 Python 后端真实数据替换
  return {
    total: 507,
    byLanguage: { Python: 132, TypeScript: 76, JavaScript: 46, 'Jupyter Notebook': 24 },
    bySource: { auto: 0, manual: 507 }
  }
}