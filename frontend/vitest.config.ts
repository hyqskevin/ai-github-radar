// vitest.config.ts — ai-github-radar
// 阶段一前端测试 config
//
// 用 happy-dom 模拟浏览器环境（vitest 默认 node 环境，UCard 之类组件需要 DOM）
// 不 include .nuxt/（自动生成）+ node_modules（避免 vitest 误跑）
//
// SPEC: docs/superpowers/specs/2026-08-10-vitest-smoke-design.md

import { defineConfig } from 'vitest/config'
import { resolve } from 'node:path'

export default defineConfig({
  resolve: {
    alias: {
      // Nuxt 注入的虚拟模块 → vitest 里 mock 掉
      '#app': resolve(__dirname, 'tests/mocks/app.ts'),
      '#imports': resolve(__dirname, 'tests/mocks/app.ts')
    }
  },
  test: {
    include: ['tests/**/*.test.ts'],
    exclude: ['node_modules', '.nuxt', '.output', 'dist'],
    environment: 'happy-dom',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary', 'html'],
      include: ['app/**/*.{ts,vue}'],
      exclude: ['app/**/*.spec.ts', 'app/**/*.test.ts', 'app/server/**']
    }
  }
})