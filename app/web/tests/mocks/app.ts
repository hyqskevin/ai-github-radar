// tests/mocks/app.ts — vitest 用，mock Nuxt 的 #app / #imports 虚拟模块
//
// mock 数据可由测试文件改写：
//   import { mockState } from '../mocks/app'
//   mockState.nextResponse = [{ id: 1, term: 'foo', ... }]

import type { Keyword } from '../../app/stores/keywords'

export const mockState: {
  nextResponse: Keyword[] | null
  nextError: { statusCode?: number; message?: string } | null
} = {
  nextResponse: null,
  nextError: null
}

export const $fetch = async <T = unknown>(path: string): Promise<T> => {
  if (mockState.nextResponse !== null) {
    const r = mockState.nextResponse
    mockState.nextResponse = null
    return r as unknown as T
  }
  if (mockState.nextError !== null) {
    const e = mockState.nextError
    mockState.nextError = null
    throw Object.assign(new Error(e.message ?? 'fetch failed'), { statusCode: e.statusCode })
  }
  // 默认：返回 404，触发 store 的 fallback mock seed 路径
  throw Object.assign(new Error('Not Found'), { statusCode: 404 })
}

export function useNuxtApp() {
  return { $fetch }
}
