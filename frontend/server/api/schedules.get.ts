// server/api/schedules.get.ts — 定时任务列表(走真后端)
import { pythonFetch } from '../utils/python'

export default defineEventHandler(async (event) => {
  const result = await pythonFetch<unknown>('/api/schedules', {
    timeoutMs: 5000,
  }, event)
  if (result.ok && result.data) {
    return result.data
  }
  return { schedules: [] }
})