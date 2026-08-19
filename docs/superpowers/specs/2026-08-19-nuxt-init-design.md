# Spec — T101 Nuxt 4 init

| 维度 | 内容 |
|---|---|
| **TODO ID** | T101（docs/TODO.md §Frontend） |
| **作者** | ai-github-radar 维护者 + AI 助手（2026-08-19） |
| **优先级** | 高 — 前端起点 |

---

## B1. 设计

### 1.1 目标

`app/web/` Nuxt 4 项目初始化 + 关键依赖装齐。

### 1.2 关键依赖

- `nuxt` ^4.x（最新 stable）
- `@nuxt/ui` ^3.x（组件库）
- `@pinia/nuxt` + `pinia`（状态管理）
- `vue`（Nuxt 自带）
- `tailwindcss` ^4.x（Nuxt UI 自带）

### 1.3 项目结构

```
app/web/
├── nuxt.config.ts
├── package.json
├── tsconfig.json
├── app.config.ts        # Nuxt UI theme
├── app/
│   ├── app.vue          # Nuxt 根组件
│   ├── layouts/
│   │   └── default.vue  # AppBar + SideNav
│   ├── pages/
│   │   ├── index.vue
│   │   ├── keywords.vue
│   │   ├── recommendations/
│   │   │   ├── index.vue
│   │   │   └── [id].vue
│   │   ├── scan.vue
│   │   ├── stars.vue
│   │   └── settings.vue
│   ├── components/      # 复用
│   ├── stores/          # Pinia
│   └── composables/
├── server/
│   └── api/             # Nitro 代理 Python /api/*
└── tests/
    └── unit/            # vitest
```

### 1.4 非目标

- ❌ SSR 部署到生产(本期本地 dev only)
- ❌ Playwright e2e(T112 一并)
- ❌ Dockerfile

---

## B2. 验收

| AC | 断言 | 怎么验 |
|---|---|---|
| AC-1 | `pnpm dev` 起服务 | bash |
| AC-2 | `curl http://127.0.0.1:5173` 返回 200 | bash |
| AC-3 | `pnpm typecheck` 通过 | bash |
| AC-4 | `nuxt.config.ts` 含 @nuxt/ui + @pinia/nuxt module | 文件检查 |

---

## B3. 测试矩阵

| C | 维度 | 覆盖 |
|---|---|---|
| C1 文件 | 关键文件存在 | AC-4 |
| C2 构建 | pnpm dev 起服务 | AC-1 |
| C3 网络 | HTTP 200 | AC-2 |

---

## B4. 风险

- **R1**：Nuxt 4 + @nuxt/ui v3 兼容性 → 固定具体版本
- **R2**：pnpm install 慢 → 不在 spec 里反复装
- **R3**：SSR 在 Nuxt UI v3 默认开 → 可保持或显式 ssr=false