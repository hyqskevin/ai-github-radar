// server/api/keywords.get.ts
// T105 AC-2: 列关键字（支持 ?source=&enabled= 过滤）
import { listKeywords } from '../utils/handlers'

export default defineEventHandler((event) => {
  const q = getQuery(event)
  return listKeywords({
    source: typeof q.source === 'string' ? q.source : undefined,
    enabled: typeof q.enabled === 'string' ? q.enabled === 'true' : undefined
  })
})