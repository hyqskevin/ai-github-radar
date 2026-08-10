// nuxt.config.ts — ai-github-radar
// Nuxt 4 SSR 全栈一体（绑 127.0.0.1，单人单机）
//
// 选型来源：SPEC.md §3 + ADR 006
// - @nuxt/ui 4 — 组件库
// - @pinia/nuxt — 状态管理
// - DESIGN.md — design token（通过 app.config.ts 注入）
// - server/api/ — Nitro HTTP 端点，调 Python 后端

export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',

  modules: [
    '@nuxt/ui',
    '@pinia/nuxt'
  ],

  devtools: { enabled: true },

  // 阶段一：单人单机，绑 loopback
  // 阶段二：可改 '0.0.0.0' + 加 auth
  devServer: {
    host: '127.0.0.1',
    port: 5173
  },

  // SSR 全栈一体（默认）
  ssr: true,

  css: ['~/assets/css/main.css'],

  typescript: {
    strict: true
  },

  // Nitro：HTTP API 端点目录
  nitro: {
    // Python 函数通过 subprocess 调用
    // 详见 app/web/server/api/*.ts
  },

  runtimeConfig: {
    // 服务端配置（不暴露给前端）
    pythonBackendUrl: process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:8765',
    public: {
      // 前端可见配置
      appName: 'ai-github-radar'
    }
  }
})