// server/api/jobs/clear.post.ts — 清空 jobs 表
import { pythonFetch } from '../../utils/python'

export default defineEventHandler(async (event) => {
  const result = await pythonFetch<unknown>('/api/jobs/clear', {
    method: 'POST',
    body: {},
    timeoutMs: 5000,
  }, event)
  if (result.ok && result.data) {
    return result.data
  }
  throw createError({ statusCode: result.status || 502, statusMessage: result.error || 'backend unavailable' })
})