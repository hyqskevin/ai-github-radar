/**
 * stores/keywords.ts — T104 Pinia keywords store
 *
 * SPEC: docs/superpowers/specs/2026-08-10-pinia-keywords-store-design.md
 *
 * 阶段一前端：用 Nuxt Nitro server/api 拉数据，后端未对接时回退 mock seed。
 */

import { defineStore } from 'pinia'
import { useNuxtApp } from '#imports'

export interface Keyword {
  id: number
  term: string
  weight: number
  source: 'auto' | 'manual'
  enabled: boolean
}

interface FetchError extends Error {
  statusCode?: number
}

// 阶段一后端未对接时的 fallback
const MOCK_KEYWORDS: Keyword[] = [
  { id: 1, term: 'agent', weight: 1.5, source: 'auto', enabled: true },
  { id: 2, term: 'claude code', weight: 2.0, source: 'manual', enabled: true },
  { id: 3, term: 'mcp', weight: 1.2, source: 'auto', enabled: false },
  { id: 4, term: 'rust', weight: 0.8, source: 'manual', enabled: true },
  { id: 5, term: 'nuxt', weight: 1.0, source: 'auto', enabled: true },
  { id: 6, term: 'typescript', weight: 1.3, source: 'manual', enabled: false }
]

// $fetch 通过 useNuxtApp() 拿（SSR-safe + 类型来自 Nuxt 自动注入）
const $nuxtFetch = () => useNuxtApp().$fetch as <T = unknown>(path: string, opts?: unknown) => Promise<T>

export const useKeywordsStore = defineStore('keywords', {
  state: () => ({
    items: [] as Keyword[],
    loading: false,
    error: null as string | null
  }),

  getters: {
    enabledItems: (state) => state.items.filter(k => k.enabled),

    bySource: (state) => ({
      auto: state.items.filter(k => k.source === 'auto'),
      manual: state.items.filter(k => k.source === 'manual')
    })
  },

  actions: {
    async fetchAll() {
      this.loading = true
      this.error = null
      try {
        const f = $nuxtFetch()
        const data = await f<Keyword[]>('/api/keywords')
        this.items = data
      } catch (err) {
        const e = err as FetchError
        if (e.statusCode === 404 || e.statusCode === undefined) {
          this.items = [...MOCK_KEYWORDS]
          this.error = 'Using mock data (backend unavailable)'
        } else {
          this.error = e.message ?? 'fetch failed'
        }
      } finally {
        this.loading = false
      }
    },

    async add(term: string, weight = 1.0): Promise<Keyword> {
      const trimmed = term.trim()
      if (!trimmed) throw new Error('term is empty or whitespace')
      if (this.items.some(k => k.term === trimmed)) {
        throw new Error(`keyword "${trimmed}" already exists`)
      }
      const f = $nuxtFetch()
      const created = await f<Keyword>('/api/keywords', {
        method: 'POST',
        body: { term: trimmed, weight }
      })
      this.items.push(created)
      return created
    },

    async update(id: number, patch: Partial<Keyword>): Promise<Keyword> {
      const idx = this.items.findIndex(k => k.id === id)
      if (idx === -1) throw new Error(`keyword id=${id} not found`)
      const f = $nuxtFetch()
      const updated = await f<Keyword>(`/api/keywords/${id}`, {
        method: 'PATCH',
        body: patch
      })
      this.items[idx] = updated
      return updated
    },

    async toggle(id: number): Promise<Keyword> {
      const existing = this.items.find(k => k.id === id)
      if (!existing) throw new Error(`keyword id=${id} not found`)
      return this.update(id, { enabled: !existing.enabled })
    },

    async remove(id: number): Promise<void> {
      const idx = this.items.findIndex(k => k.id === id)
      if (idx === -1) throw new Error(`keyword id=${id} not found`)
      const f = $nuxtFetch()
      await f(`/api/keywords/${id}`, { method: 'DELETE' })
      this.items.splice(idx, 1)
    },

    $reset() {
      this.items = []
      this.loading = false
      this.error = null
    }
  }
})