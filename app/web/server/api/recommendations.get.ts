// server/api/recommendations.get.ts
// T105 AC-4: 列推荐
import { listRecommendations } from '../utils/handlers'

export default defineEventHandler((event) => {
  const q = getQuery(event)
  return listRecommendations({
    limit: typeof q.limit === 'string' ? Number(q.limit) : undefined,
    offset: typeof q.offset === 'string' ? Number(q.offset) : undefined
  })
})