// T105 新增端点测试 — stars / recommendations schema / page tests

import { describe, expect, it, beforeEach } from 'vitest'
import {
  _resetStore,
  listStars,
  getStarsStats,
  listRecommendations,
  createRecommendation,
} from '../../server/utils/handlers'

beforeEach(() => _resetStore())

describe('T105 stars endpoints', () => {
  it('listStars returns repo list', () => {
    const stars = listStars()
    expect(stars.length).toBeGreaterThan(0)
    expect(stars[0]).toHaveProperty('id')
    expect(stars[0]).toHaveProperty('owner')
    expect(stars[0]).toHaveProperty('name')
  })

  it('listStars respects limit', () => {
    expect(listStars({ limit: 2 }).length).toBe(2)
    expect(listStars({ limit: 1 }).length).toBe(1)
  })

  it('getStarsStats returns total + by_language + top_topics', () => {
    const s = getStarsStats()
    expect(s.total).toBeGreaterThan(0)
    expect(typeof s.by_language).toBe('object')
    expect(Array.isArray(s.top_topics)).toBe(true)
    expect(s.top_topics[0]).toHaveProperty('name')
    expect(s.top_topics[0]).toHaveProperty('count')
  })

  it('getStarsStats top_topics sorted descending', () => {
    const s = getStarsStats()
    for (let i = 1; i < s.top_topics.length; i++) {
      expect(s.top_topics[i - 1].count).toBeGreaterThanOrEqual(s.top_topics[i].count)
    }
  })
})

describe('T105 recommendations wrapper', () => {
  it('listRecommendations returns array', () => {
    const recs = listRecommendations()
    expect(Array.isArray(recs)).toBe(true)
  })

  it('createRecommendation assigns id + created_at', () => {
    const r = createRecommendation({
      repo_id: 100,
      score: 5.5,
      matched_keywords: 'fastapi',
      channel: 'local',
    })
    expect(r.id).toBeGreaterThan(0)
    expect(r.created_at).toBeTruthy()
    expect(r.repo_id).toBe(100)
  })

  it('listRecommendations returns descending by id', () => {
    const a = createRecommendation({ repo_id: 1, score: 1, matched_keywords: '', channel: 'local' })
    const b = createRecommendation({ repo_id: 2, score: 2, matched_keywords: '', channel: 'local' })
    const list = listRecommendations()
    // b > a → b first
    expect(list[0].id).toBe(b.id)
    expect(list[1].id).toBe(a.id)
  })
})