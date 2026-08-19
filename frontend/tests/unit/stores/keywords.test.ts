/**
 * keywords.test.ts — T104 Pinia keywords store
 *
 * SPEC: docs/superpowers/specs/2026-08-10-pinia-keywords-store-design.md
 *
 * 覆盖 7 维度（C1/C2/C4/C5/C8/DOC/ERR），8 case。
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

import { mockState } from '../../mocks/app'
import { useKeywordsStore } from '../../../app/stores/keywords'
import type { Keyword } from '../../../app/stores/keywords'

describe('T104 keywords store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockState.nextResponse = null
    mockState.nextError = null
  })

  // AC-1 happy: store 初始状态
  it('DOC: store starts with empty items, no error', () => {
    const store = useKeywordsStore()
    expect(store.items).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  // AC-1 happy: fetchAll 成功
  it('happy (C8): fetchAll loads keywords from /api/keywords', async () => {
    const mockData: Keyword[] = [
      { id: 1, term: 'agent', weight: 1.5, source: 'auto', enabled: true },
      { id: 2, term: 'claude code', weight: 2.0, source: 'manual', enabled: true }
    ]
    mockState.nextResponse = mockData
    const store = useKeywordsStore()
    await store.fetchAll()
    expect(store.items).toEqual(mockData)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  // AC-4 ERR: fetchAll 失败回退到 mock
  it('error (C1): fetchAll on HTTP 404 falls back to mock seed', async () => {
    mockState.nextError = { statusCode: 404, message: 'Not Found' }
    const store = useKeywordsStore()
    await store.fetchAll()
    expect(store.items.length, 'should fall back to mock seed').toBeGreaterThan(0)
    expect(store.error, 'should record fallback notice').toMatch(/mock/i)
  })

  // AC-1 + AC-3 ERR: add 重复 term 抛错
  it('error (ERR): add with duplicate term throws', async () => {
    mockState.nextResponse = [{ id: 1, term: 'vue', weight: 1, source: 'auto', enabled: true }]
    const store = useKeywordsStore()
    await store.fetchAll()
    await expect(store.add('vue')).rejects.toThrow(/duplicate|already/i)
  })

  // AC-3 ERR: add 空字符串
  it('error (ERR): add empty/whitespace string throws', async () => {
    const store = useKeywordsStore()
    await expect(store.add('')).rejects.toThrow(/empty|whitespace/i)
    await expect(store.add('   ')).rejects.toThrow(/empty|whitespace/i)
  })

  // AC-1 + AC-3 ERR: update / remove 不存在的 id
  it('error (ERR): update / remove on non-existent id throws', async () => {
    const store = useKeywordsStore()
    await expect(store.update(999, { weight: 2 })).rejects.toThrow(/not found/i)
    await expect(store.remove(999)).rejects.toThrow(/not found/i)
  })

  // AC-2 C8: getters 类型断言
  it('happy (C2/C8): getters enabledItems and bySource return filtered subsets', async () => {
    const mockData: Keyword[] = [
      { id: 1, term: 'a', weight: 1, source: 'auto', enabled: true },
      { id: 2, term: 'b', weight: 1, source: 'manual', enabled: false },
      { id: 3, term: 'c', weight: 1, source: 'auto', enabled: false }
    ]
    mockState.nextResponse = mockData
    const store = useKeywordsStore()
    await store.fetchAll()

    expect(store.enabledItems.map(k => k.id)).toEqual([1])
    expect(store.bySource.auto.map(k => k.id)).toEqual([1, 3])
    expect(store.bySource.manual.map(k => k.id)).toEqual([2])
  })

  // AC-5: $reset
  it('happy (C8): $reset clears state', async () => {
    mockState.nextResponse = [{ id: 1, term: 'x', weight: 1, source: 'auto', enabled: true }]
    const store = useKeywordsStore()
    await store.fetchAll()
    store.error = 'manual error'
    store.$reset()
    expect(store.items).toEqual([])
    expect(store.error).toBeNull()
    expect(store.loading).toBe(false)
  })
})