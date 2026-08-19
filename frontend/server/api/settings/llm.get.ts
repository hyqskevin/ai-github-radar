// server/api/settings/llm.get.ts — LLM 设置读
import { pythonFetch } from '../../utils/python'

export default defineEventHandler(async (event) => {
  const result = await pythonFetch<unknown>('/api/settings/llm', {
    timeoutMs: 5000,
  }, event)
  if (result.ok && result.data) {
    return result.data
  }
  return {
    provider: 'none',
    model: '',
    api_key_set: false,
    enabled: false,
    backend_unavailable: true,
  }
})