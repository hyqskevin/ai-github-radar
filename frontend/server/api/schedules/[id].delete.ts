// server/api/schedules/[id].delete.ts — 删除定时任务
import { pythonFetch } from '../../utils/python'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  const result = await pythonFetch<unknown>(`/api/schedules/${id}`, {
    method: 'DELETE',
    timeoutMs: 5000,
  }, event)
  if (result.ok && result.data) {
    return result.data
  }
  throw createError({ statusCode: result.status || 502, statusMessage: result.error || 'backend unavailable' })
})