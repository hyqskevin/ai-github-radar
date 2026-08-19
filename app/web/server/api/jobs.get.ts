// server/api/jobs.get.ts — 任务监控列表(走真后端)
import { pythonFetch } from '../utils/python'

export default defineEventHandler(async (event) => {
  const q = getQuery(event)
  const params: Record<string, string | number> = {}
  if (typeof q.limit === 'string') params.limit = Number(q.limit)

  const result = await pythonFetch<unknown>('/api/jobs', {
    query: params,
    timeoutMs: 5000,
  }, event)
  if (result.ok && result.data) {
    return result.data
  }
  return { jobs: [], limit: params.limit ?? 50 }
})