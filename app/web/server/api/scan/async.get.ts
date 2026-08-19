// server/api/scan/async.get.ts — GET fallback (查最近 scan status)
import { pythonFetch } from '../../utils/python'

export default defineEventHandler(async (event) => {
  const result = await pythonFetch<unknown>('/api/scan/async', {
    timeoutMs: 5000,
  }, event)
  if (result.ok && result.data) {
    return result.data
  }
  return { jobs: [], limit: 50 }
})