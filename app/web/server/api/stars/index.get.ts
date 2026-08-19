// server/api/stars.get.ts
// T105 AC-4: 列 star 仓库
import { listStars } from '../../utils/handlers'

export default defineEventHandler((event) => {
  const q = getQuery(event)
  return listStars({
    limit: typeof q.limit === 'string' ? Number(q.limit) : undefined,
  })
})