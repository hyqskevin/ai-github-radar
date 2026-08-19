// server/api/keywords.get.ts
// T105 AC-2 + T112: 列关键字(优先真后端,fallback mock)
import { listKeywords } from '../utils/handlers'
import { pythonFetch } from '../utils/python'

export default defineEventHandler(async (event) => {
  const q = getQuery(event)
  const params: Record<string, string> = {}
  if (typeof q.source === 'string') params.source = q.source
  if (typeof q.enabled === 'string') params.enabled = q.enabled

  // 优先调 Python 后端(阶段二)
  const result = await pythonFetch<unknown>('/api/keywords', {
    query: params,
    timeoutMs: 2000,
  }, event)
  if (result.ok && result.data) {
    // Python 后端返 {keywords: [...]} 或 list — 两种都接受
    return result.data
  }
  // fallback: Nitro mock store
  return listKeywords({
    source: params.source,
    enabled: params.enabled ? params.enabled === 'true' : undefined,
  })
})