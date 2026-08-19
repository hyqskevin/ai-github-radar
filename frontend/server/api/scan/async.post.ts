// server/api/scan/async.post.ts — 触发 scan(后台)
import { pythonFetch } from '../../utils/python'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const result = await pythonFetch<unknown>('/api/scan/async', {
    method: 'POST',
    body: body || {},
    timeoutMs: 5000,
  }, event)
  if (result.ok && result.data) {
    return result.data
  }
  throw createError({ statusCode: result.status || 502, statusMessage: result.error || 'backend unavailable' })
})