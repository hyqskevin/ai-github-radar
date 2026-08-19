// T112 python.ts unit tests

import { describe, expect, it, vi, afterEach, beforeEach } from 'vitest'
import { pythonFetch, getPythonBackendUrl } from '../../server/utils/python'

// Mock global fetch
const originalFetch = globalThis.fetch

afterEach(() => {
  globalThis.fetch = originalFetch
})

describe('T112 getPythonBackendUrl', () => {
  it('returns default 127.0.0.1:8765 when no config', () => {
    delete process.env.PYTHON_BACKEND_URL
    const url = getPythonBackendUrl()
    expect(url).toContain('127.0.0.1:8765')
  })

  it('honors PYTHON_BACKEND_URL env', () => {
    process.env.PYTHON_BACKEND_URL = 'http://py.example.com:9000'
    expect(getPythonBackendUrl()).toBe('http://py.example.com:9000')
  })
})

describe('T112 pythonFetch', () => {
  beforeEach(() => {
    process.env.PYTHON_BACKEND_URL = 'http://py.test:8765'
  })

  it('returns ok + data on 200 response', async () => {
    globalThis.fetch = vi.fn(async () =>
      new Response(JSON.stringify({ keywords: [{ id: 1, term: 'x' }] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    ) as any

    const r = await pythonFetch<{ keywords: any[] }>('/api/keywords')
    expect(r.ok).toBe(true)
    expect(r.status).toBe(200)
    expect(r.data?.keywords.length).toBe(1)
    expect(r.error).toBeNull()
  })

  it('returns ok=false on 500', async () => {
    globalThis.fetch = vi.fn(async () =>
      new Response('internal error', { status: 500 })
    ) as any

    const r = await pythonFetch('/api/x')
    expect(r.ok).toBe(false)
    expect(r.status).toBe(500)
    expect(r.error).toContain('internal error')
  })

  it('returns error on network failure', async () => {
    globalThis.fetch = vi.fn(async () => {
      throw new Error('ECONNREFUSED')
    }) as any

    const r = await pythonFetch('/api/x', { timeoutMs: 1000 })
    expect(r.ok).toBe(false)
    expect(r.status).toBe(0)
    expect(r.error).toContain('ECONNREFUSED')
  })

  it('timeout aborts fetch', async () => {
    globalThis.fetch = vi.fn(async (_url, init: any) =>
      new Promise((_, reject) => {
        init?.signal?.addEventListener('abort', () =>
          reject(new DOMException('aborted', 'AbortError'))
        )
      })
    ) as any

    const r = await pythonFetch('/api/x', { timeoutMs: 50 })
    expect(r.ok).toBe(false)
    expect(r.error).toBe('timeout')
  })

  it('appends query params to URL', async () => {
    let capturedUrl = ''
    globalThis.fetch = vi.fn(async (url: any) => {
      capturedUrl = url.toString()
      return new Response(JSON.stringify({ ok: true }), { status: 200 })
    }) as any

    await pythonFetch('/api/keywords', { query: { source: 'auto', limit: 10 } })
    expect(capturedUrl).toContain('source=auto')
    expect(capturedUrl).toContain('limit=10')
  })

  it('sends POST body as JSON', async () => {
    let captured: any = null
    globalThis.fetch = vi.fn(async (_url: any, init: any) => {
      captured = init
      return new Response('{}', { status: 200 })
    }) as any

    await pythonFetch('/api/keywords', {
      method: 'POST',
      body: { term: 'fastapi', weight: 5.0 },
    })
    expect(captured.method).toBe('POST')
    expect(captured.headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(captured.body)).toEqual({ term: 'fastapi', weight: 5.0 })
  })
})