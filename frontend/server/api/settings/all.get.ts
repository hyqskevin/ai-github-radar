// server/api/settings/all.get.ts — 读所有 settings
import { pythonFetch } from '../../utils/python'

export default defineEventHandler(async (event) => {
  const result = await pythonFetch<unknown>('/api/settings/all', {
    timeoutMs: 5000,
  }, event)
  if (result.ok && result.data) {
    return result.data
  }
  return {}
})