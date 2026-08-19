// server/api/settings/all.post.ts — 写所有 settings
import { pythonFetch } from '../../utils/python'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const result = await pythonFetch<unknown>('/api/settings/all', {
    method: 'POST',
    body,
    timeoutMs: 5000,
  }, event)
  if (result.ok && result.data) {
    return result.data
  }
  throw createError({ statusCode: result.status || 502, statusMessage: result.error || 'backend unavailable' })
})