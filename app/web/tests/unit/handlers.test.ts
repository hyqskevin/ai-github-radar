/**
 * handlers.test.ts — T105 单元测试（handler 函数）
 *
 * 测 server/utils/handlers.ts 暴露的纯函数，绕过 Nitro 框架。
 * SPEC: docs/superpowers/specs/2026-08-10-nitro-http-design.md
 *
 * 覆盖 6 维度（C1/C2/C5/C7/DOC/ERR），12 case。
 */

import { describe, it, expect, beforeEach } from 'vitest'
import {
  getHealth,
  listKeywords,
  createKeyword,
  updateKeyword,
  deleteKeyword,
  listRecommendations,
  createRecommendation,
  runScan,
  getStarsStats,
  HttpError,
  _resetStore
} from '../../server/utils/handlers'

describe('T105 handlers', () => {
  beforeEach(() => {
    _resetStore()
  })

  // AC-1
  it('DOC (C1): getHealth returns status + service + ISO timestamp', () => {
    const h = getHealth()
    expect(h.status).toBe('ok')
    expect(h.service).toBe('ai-github-radar-web')
    expect(h.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)
  })

  // AC-2
  it('DOC (C1): listKeywords returns 6 mock seed by default', () => {
    const items = listKeywords()
    expect(items.length).toBe(6)
    expect(items[0]).toHaveProperty('id')
    expect(items[0]).toHaveProperty('term')
    expect(items[0]).toHaveProperty('weight')
    expect(items[0]).toHaveProperty('source')
    expect(items[0]).toHaveProperty('enabled')
  })

  // AC-2 happy
  it('happy (C1): createKeyword returns new keyword with source=manual', () => {
    const k = createKeyword({ term: 'foo', weight: 1.5 })
    expect(k.term).toBe('foo')
    expect(k.weight).toBe(1.5)
    expect(k.source).toBe('manual')
    expect(k.enabled).toBe(true)
    expect(k.id).toBeGreaterThan(6)  // 6 mock seed
  })

  // AC-2 update
  it('happy (C1): updateKeyword patches weight', () => {
    const updated = updateKeyword(1, { weight: 2.5 })
    expect(updated.id).toBe(1)
    expect(updated.weight).toBe(2.5)
    expect(updated.term).toBe('agent')  // 其它不变
  })

  // AC-2 delete
  it('happy (C1): deleteKeyword removes from list', () => {
    deleteKeyword(1)
    const items = listKeywords()
    expect(items.find(k => k.id === 1)).toBeUndefined()
    expect(items.length).toBe(5)
  })

  // AC-3 400: 缺 term
  it('error (ERR/C7): createKeyword without term throws 400', () => {
    expect(() => createKeyword({ weight: 1 })).toThrow(HttpError)
    try { createKeyword({ weight: 1 }) } catch (e) {
      expect((e as HttpError).statusCode).toBe(400)
    }
  })

  // AC-3 400: 空 term
  it('error (ERR/C7): createKeyword with empty/whitespace term throws 400', () => {
    expect(() => createKeyword({ term: '', weight: 1 })).toThrow(HttpError)
    expect(() => createKeyword({ term: '   ', weight: 1 })).toThrow(HttpError)
  })

  // AC-3 400: weight 非数字
  it('error (ERR/C7): createKeyword with non-number weight throws 400', () => {
    expect(() => createKeyword({ term: 'x', weight: 'foo' as unknown as number })).toThrow(HttpError)
  })

  // AC-3 409: 重复
  it('error (ERR/C7): createKeyword with duplicate term throws 409', () => {
    expect(() => createKeyword({ term: 'agent', weight: 1 })).toThrow(HttpError)
    try { createKeyword({ term: 'agent', weight: 1 }) } catch (e) {
      expect((e as HttpError).statusCode).toBe(409)
    }
  })

  // AC-3 404: PATCH 不存在
  it('error (ERR/C7): updateKeyword on non-existent id throws 404', () => {
    expect(() => updateKeyword(999, { weight: 2 })).toThrow(HttpError)
    try { updateKeyword(999, { weight: 2 }) } catch (e) {
      expect((e as HttpError).statusCode).toBe(404)
    }
  })

  // AC-3 404: DELETE 不存在
  it('error (ERR/C7): deleteKeyword on non-existent id throws 404', () => {
    expect(() => deleteKeyword(999)).toThrow(HttpError)
    try { deleteKeyword(999) } catch (e) {
      expect((e as HttpError).statusCode).toBe(404)
    }
  })

  // AC-4
  it('DOC (C1): getStarsStats returns stats object', () => {
    const s = getStarsStats()
    expect(s).toHaveProperty('total')
    expect(s).toHaveProperty('byLanguage')
    expect(s).toHaveProperty('bySource')
    expect(typeof s.total).toBe('number')
  })

  // AC-4
  it('DOC (C1): runScan returns status + matched + pushed', () => {
    const r = runScan({ dryRun: true })
    expect(r.status).toBe('ok')
    expect(typeof r.matched).toBe('number')
    expect(r.pushed).toBe(0)  // dryRun
  })

  // bonus: listRecommendations / createRecommendation
  it('DOC (C1): listRecommendations returns sorted by id desc', () => {
    const r1 = createRecommendation({ repo_id: 1, owner: 'a', name: 'b', score: 1, matched_keywords: ['x'] })
    const r2 = createRecommendation({ repo_id: 2, owner: 'c', name: 'd', score: 2, matched_keywords: [] })
    const list = listRecommendations()
    expect(list[0].id).toBe(r2.id)
    expect(list[1].id).toBe(r1.id)
  })
})