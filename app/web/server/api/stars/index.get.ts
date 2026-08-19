// server/api/stars/index.get.ts
// 列我的 star 仓库 — 走真后端,fallback mock
import { pythonFetch } from '../../utils/python'
import { listStars } from '../../utils/handlers'

export default defineEventHandler(async (event) => {
  const q = getQuery(event)
  const params: Record<string, string | number> = {}
  if (typeof q.limit === 'string') params.limit = Number(q.limit)
  if (typeof q.offset === 'string') params.offset = Number(q.offset)

  const result = await pythonFetch<unknown>('/api/stars', {
    query: params,
    timeoutMs: 5000,
  }, event)
  if (result.ok && result.data) {
    return result.data
  }
  return { stars: listStars({ limit: params.limit }) }
})