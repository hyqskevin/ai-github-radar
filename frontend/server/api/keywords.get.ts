// server/api/keywords.get.ts
// T105 AC-2 + T112: 列关键字(走真后端,空 fallback)
import { pythonFetch } from '../utils/python'
import { listKeywords } from '../utils/handlers'

export default defineEventHandler(async (event) => {
  const q = getQuery(event)
  const params: Record<string, string> = {}
  if (typeof q.source === 'string') params.source = q.source
  if (typeof q.enabled === 'string') params.enabled = q.enabled

  const result = await pythonFetch<unknown>('/api/keywords', {
    query: params,
    timeoutMs: 5000,
  }, event)
  if (result.ok && result.data) {
    return result.data
  }
  // fallback: Nitro mock seed(只在后端完全不可达时)
  return listKeywords({
    source: params.source,
    enabled: params.enabled ? params.enabled === 'true' : undefined,
  })
})