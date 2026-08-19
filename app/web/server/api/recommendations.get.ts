// server/api/recommendations.get.ts
// 列推荐 — 走真后端,fallback 空 list
import { pythonFetch } from '../utils/python'
import { listRecommendations } from '../utils/handlers'

export default defineEventHandler(async (event) => {
  const q = getQuery(event)
  const params: Record<string, string | number> = {}
  if (typeof q.limit === 'string') params.limit = Number(q.limit)
  if (typeof q.offset === 'string') params.offset = Number(q.offset)

  const result = await pythonFetch<any>('/api/recommendations', {
    query: params,
    timeoutMs: 5000,
  }, event)
  if (result.ok && result.data) {
    // Python 后端返 {recommendations: [...]} — 透传
    return result.data
  }
  return { recommendations: listRecommendations({
    limit: typeof params.limit === 'number' ? params.limit : undefined,
    offset: typeof params.offset === 'number' ? params.offset : undefined,
  }) }
})