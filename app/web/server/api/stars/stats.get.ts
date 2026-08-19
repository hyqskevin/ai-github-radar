// server/api/stars/stats.get.ts
// 列 stars 统计 — 走真后端,fallback mock
import { pythonFetch } from '../../utils/python'
import { getStarsStats } from '../../utils/handlers'

export default defineEventHandler(async (event) => {
  const result = await pythonFetch<unknown>('/api/stars/stats', {
    timeoutMs: 5000,
  }, event)
  if (result.ok && result.data) {
    return result.data
  }
  return getStarsStats()
})