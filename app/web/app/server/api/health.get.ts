// server/api/health.get.ts
// 健康检查端点：返回后端状态 + 版本
// 见 docs/api-doc.md

export default defineEventHandler(() => {
  return {
    status: 'ok',
    service: 'ai-github-radar-web',
    timestamp: new Date().toISOString()
  }
})
