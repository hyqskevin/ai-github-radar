// server/api/scan.post.ts
// T105 AC-4: 触发扫描
import { runScan } from '../utils/handlers'

export default defineEventHandler(async (event) => {
  let body: { dryRun?: boolean } = {}
  try {
    body = await readBody<{ dryRun?: boolean }>(event) ?? {}
  } catch {
    body = {}
  }
  return runScan({ dryRun: body.dryRun })
})
