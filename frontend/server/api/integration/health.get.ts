// server/api/integration/health.get.ts
// T112 AC-1: 检测 Python FastAPI 后端是否可达
//
// 接受 ?url=<override> 参数(测试用),默认读 runtimeConfig.pythonBackendUrl
import { pythonFetch } from '../../utils/python'

export default defineEventHandler(async (event) => {
  const q = getQuery(event)
  const url = typeof q.url === 'string' ? q.url : undefined

  let cfg: any = null
  try {
    cfg = useRuntimeConfig(event)
  } catch {
    // not in Nitro context
  }
  const configured = cfg?.pythonBackendUrl ?? process.env.PYTHON_BACKEND_URL ?? 'http://127.0.0.1:8765'

  // 如果传了 url,override(测试用)
  const target = url ?? configured

  const result = await pythonFetch<unknown>('/api/keywords', {
    timeoutMs: 2000,
  }, event)
  // 重新 fetch 走 override URL(需要传 event + 透传)
  let reachable = result.ok
  let status = result.status
  let error = result.error
  let actualUrl = configured
  if (url) {
    // 手动用 override url 调一次
    try {
      const r = await fetch(new URL('/api/keywords', url), {
        signal: AbortSignal.timeout(2000),
      })
      reachable = r.ok
      status = r.status
      actualUrl = url
      if (!r.ok) error = await r.text()
    } catch (e: any) {
      reachable = false
      status = 0
      error = e?.message ?? 'fetch failed'
      actualUrl = url
    }
  }
  return {
    python_reachable: reachable,
    python_status: status,
    python_error: error,
    python_url: actualUrl,
    timestamp: new Date().toISOString(),
  }
})