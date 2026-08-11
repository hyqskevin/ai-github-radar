/**
 * utils/mock-data.ts — 阶段一 fallback 数据
 *
 * reco / stars / scan 的 store 还没建（阶段二），T106 页面用这些 mock。
 */

export interface MockRecommendation {
  id: number
  owner: string
  name: string
  score: number
  matched_keywords: string[]
  created_at: string
}

export interface MockStarsStats {
  total: number
  byLanguage: Record<string, number>
  bySource: { auto: number; manual: number }
}

const NOW = new Date().toISOString()

export const mockRecommendations: MockRecommendation[] = [
  { id: 1, owner: 'obra', name: 'superpowers', score: 9.2, matched_keywords: ['agent', 'skill', 'claude'], created_at: NOW },
  { id: 2, owner: 'firecrawl', name: 'firecrawl', score: 8.8, matched_keywords: ['context', 'scrape'], created_at: NOW },
  { id: 3, owner: 'msitarzewski', name: 'agency-agents', score: 8.5, matched_keywords: ['agent', 'claude'], created_at: NOW },
  { id: 4, owner: 'github', name: 'spec-kit', score: 8.1, matched_keywords: ['spec', 'claude code'], created_at: NOW },
  { id: 5, owner: 'browser-use', name: 'browser-use', score: 7.9, matched_keywords: ['agent', 'browser'], created_at: NOW },
  { id: 6, owner: 'unclecode', name: 'crawl4ai', score: 7.5, matched_keywords: ['llm', 'scrape'], created_at: NOW }
]

export const mockStarsStats: MockStarsStats = {
  total: 507,
  byLanguage: { Python: 132, TypeScript: 76, JavaScript: 46, 'Jupyter Notebook': 24 },
  bySource: { auto: 0, manual: 507 }
}