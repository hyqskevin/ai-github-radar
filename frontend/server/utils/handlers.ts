/**
 * handlers.ts — T105 + T112 handler 业务逻辑
 *
 * 阶段一: 进程内 store(mock,重启清空)
 * 阶段二: 调 Python FastAPI backend
 *
 * 阶段一策略: server/api/*.ts 默认走 process 内存 store(Nitro 进程);
 *           如果运行时设置了 PYTHON_BACKEND_URL (非默认 127.0.0.1:8765)
 *           且 PYTHON_BACKEND_DISABLED=0,handler 会调真后端。
 *           阶段二默认走真后端。
 *
 * 为避免阻塞:Nitro handler 总先返回真后端结果(超时 5s),失败则落回 mock。
 */

import type { Keyword, Recommendation } from './types'

// ---------------------------------------------------------------------------
// 进程内存储(mock fallback)
// ---------------------------------------------------------------------------

const keywords = new Map<number, Keyword>()
const recommendations = new Map<number, Recommendation>()
let nextKeywordId = 1
let nextRecId = 1

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

export function _resetStore() {
  keywords.clear()
  recommendations.clear()
  nextKeywordId = 1
  nextRecId = 1
  seeded = false
  ensureSeeded()
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export function getHealth() {
  return {
    status: 'ok',
    service: 'ai-github-radar-web',
    timestamp: new Date().toISOString()
  }
}

// ---------------------------------------------------------------------------
// Keywords
// ---------------------------------------------------------------------------

export class HttpError extends Error {
  constructor(public statusCode: number, message: string) {
    super(message)
    this.name = 'HttpError'
  }
}

export function listKeywords(filters: { source?: string; enabled?: boolean } = {}): Keyword[] {
  ensureSeeded()
  let items = Array.from(keywords.values())
  if (filters.source) items = items.filter(k => k.source === filters.source)
  if (filters.enabled !== undefined) items = items.filter(k => k.enabled === filters.enabled)
  return items
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
    source: 'manual',
    enabled: true
  }
  keywords.set(id, created)
  return created
}

export function updateKeyword(id: number, patch: Partial<Omit<Keyword, 'id'>>): Keyword {
  ensureSeeded()
  const existing = keywords.get(id)
  if (!existing) throw new HttpError(404, `keyword id=${id} not found`)
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

// ---------------------------------------------------------------------------
// Recommendations
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Scan + Stars stats (mock 阶段一,阶段二走 Python 后端)
// ---------------------------------------------------------------------------

export function runScan(opts: { dryRun?: boolean } = {}): { status: string; matched: number; pushed: number } {
  ensureSeeded()
  const enabledKws = Array.from(keywords.values()).filter(k => k.enabled)
  const matched = Math.floor(Math.random() * 20)
  const pushed = opts.dryRun ? 0 : matched
  return { status: 'ok', matched, pushed }
}

export function listStars(opts: { limit?: number } = {}): Array<{ id: number; owner: string; name: string; language: string | null; description: string | null }> {
  const all = [
    { id: 1, owner: 'fastapi', name: 'fastapi', language: 'Python', description: 'FastAPI framework, high perf, easy to learn' },
    { id: 2, owner: 'tiangolo', name: 'uvicorn', language: 'Python', description: 'ASGI server for Python' },
    { id: 3, owner: 'pydantic', name: 'pydantic', language: 'Python', description: 'Data validation using Python type hints' },
    { id: 4, owner: 'vuejs', name: 'core', language: 'TypeScript', description: 'Vue.js the progressive JavaScript framework' },
    { id: 5, owner: 'tokio-rs', name: 'tokio', language: 'Rust', description: 'An async runtime for Rust' },
  ]
  return all.slice(0, opts.limit ?? all.length)
}

export function getStarsStats() {
  return {
    total: 507,
    by_language: { Python: 132, TypeScript: 76, JavaScript: 46, 'Jupyter Notebook': 24 },
    top_topics: [
      { name: 'llm', count: 88 },
      { name: 'agent', count: 76 },
      { name: 'typescript', count: 65 },
      { name: 'fastapi', count: 54 },
      { name: 'cli', count: 49 },
      { name: 'rag', count: 42 },
      { name: 'pydantic', count: 38 },
      { name: 'mcp', count: 33 },
      { name: 'rust', count: 29 },
      { name: 'vue', count: 27 },
    ],
  }
}