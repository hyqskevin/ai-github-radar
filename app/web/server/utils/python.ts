/**
 * python.ts — Nitro → Python FastAPI backend HTTP client (T112).
 *
 * 设计: 在 Nitro handler 内调 Python FastAPI (default: http://127.0.0.1:8765/api/*)
 * 如果后端不可达,handler 应回落到 mock store(阶段一容错策略)。
 */

import type { H3Event } from 'h3'

export interface PythonFetchOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  query?: Record<string, string | number | undefined>
  headers?: Record<string, string>
  timeoutMs?: number
}

export interface PythonFetchResult<T> {
  ok: boolean
  status: number
  data: T | null
  error: string | null
}

export function getPythonBackendUrl(event?: H3Event): string {
  // 优先从 runtime config 读(server-only)
  try {
    // @ts-ignore — Nitro auto-imports useRuntimeConfig
    const cfg = useRuntimeConfig(event)
    return cfg.pythonBackendUrl || 'http://127.0.0.1:8765'
  } catch {
    return process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8765'
  }
}

export async function pythonFetch<T = unknown>(
  path: string,
  options: PythonFetchOptions = {},
  event?: H3Event
): Promise<PythonFetchResult<T>> {
  const base = getPythonBackendUrl(event)
  const url = new URL(path, base)
  if (options.query) {
    for (const [k, v] of Object.entries(options.query)) {
      if (v !== undefined) url.searchParams.set(k, String(v))
    }
  }
  const controller = new AbortController()
  const timeout = setTimeout(
    () => controller.abort(),
    options.timeoutMs ?? 5000
  )
  try {
    const resp = await fetch(url, {
      method: options.method ?? 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers ?? {}),
      },
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    })
    if (!resp.ok) {
      const text = await resp.text()
      return {
        ok: false,
        status: resp.status,
        data: null,
        error: text || resp.statusText,
      }
    }
    const data = (await resp.json()) as T
    return { ok: true, status: resp.status, data, error: null }
  } catch (e: any) {
    return {
      ok: false,
      status: 0,
      data: null,
      error: e?.name === 'AbortError' ? 'timeout' : (e?.message ?? 'fetch failed'),
    }
  } finally {
    clearTimeout(timeout)
  }
}