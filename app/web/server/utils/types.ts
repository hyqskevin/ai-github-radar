/**
 * types.ts — T105 共享类型
 * SPEC: docs/superpowers/specs/2026-08-10-nitro-http-design.md
 */

export interface Keyword {
  id: number
  term: string
  weight: number
  source: 'auto' | 'manual'
  enabled: boolean
}

export interface Recommendation {
  id: number
  repo_id: number
  owner: string
  name: string
  score: number
  matched_keywords: string[]
  created_at: string  // ISO 8601
}