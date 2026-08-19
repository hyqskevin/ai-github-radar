// server/api/schedules/[id].patch.ts — 更新定时任务
import { pythonFetch } from '../../utils/python'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  const body = await readBody(event)
  const result = await pythonFetch<unknown>(`/api/schedules/${id}`, {
    method: 'PATCH',
    body,
    timeoutMs: 5000,
  }, event)
  if (result.ok && result.data) {
    return result.data
  }
  throw createError({ statusCode: result.status || 502, statusMessage: result.error || 'backend unavailable' })
})