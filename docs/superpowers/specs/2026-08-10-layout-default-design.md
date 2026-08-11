# Spec — T103 layouts/default.vue

**TODO**: T103
**日期**: 2026-08-10
**状态**: proposed

---

## B1 设计

### 目标

把 `app/web/app/layouts/default.vue`（AppBar + SideNav + Content 三段式）加测试覆盖。当前 layout 已有实际渲染（dev server 跑通），但**没有 vitest 守护**——任何手改都不会被测试发现。

### 当前 layout 结构

```vue
<template>
  <div class="h-screen flex flex-col bg-default text-default">
    <!-- AppBar: 56px 高，sticky top -->
    <header class="h-14 shrink-0 border-b ...">
      <NuxtLink to="/">ai-github-radar</NuxtLink>
      <UColorModeButton />
      <UButton to="/settings" icon="i-lucide-settings" />
    </header>
    <!-- Body: SideNav + Content -->
    <div class="flex flex-1 min-h-0">
      <aside class="w-60 shrink-0 border-r ...">
        <UVerticalNavigation :items="navItems" />
      </aside>
      <main>
        <slot />
      </main>
    </div>
  </div>
</template>
```

### 测试策略

不用 `@vue/test-utils`（避免 Vue 编译路径噪音，跟 T101 一致）。改用：

1. **静态断言**：直接读 `.vue` 文件源码，用 regex 检查关键 class / element / 文本
2. **编译产物断言**：Nuxt prepare 后看 `.nuxt/components.d.ts` 里 layout 自动注册
3. **样式一致性**：用 4 倍数间距（DESIGN.md principle）验证 Tailwind class

### 测试覆盖维度

| 维度 | 覆盖什么 |
|---|---|
| **C6 UI 渲染** | AppBar / SideNav / Content 三段都存在 |
| **C7 Props / 边界** | navItems 是非空数组 / 每个 item 有 label + icon + to |
| **DOC** | DESIGN.md 提到的 4 倍数间距被 layout 遵守 |
| **ERR** | layout 文件存在且含 3 个核心区块 |

### out of scope

- snapshot 测试（阶段二 snapshot 工具稳定后再加）
- e2e 浏览器渲染（playwright，T106 一起）
- 视觉回归（percy / chromatic，阶段三）

---

## B2 验收（AC）

### AC-1：layout 文件存在

- `app/web/app/layouts/default.vue` 存在
- 含 `<header>` / `<aside>` / `<main>` 三个标签

### AC-2：AppBar 完整性

- 含 logo NuxtLink（指向 `/`）
- 含 `<UColorModeButton />`（theme switch）
- 含 settings NuxtLink / UButton（指向 `/settings`）

### AC-3：SideNav 完整性

- `navItems` 是非空数组（≥ 6 项）
- 每项含 label / icon / to 三个字段
- icon 都是 `i-lucide-*` 命名（Nuxt Icon 解析）

### AC-4：Content slot

- `<main>` 内含 `<slot />`
- main 元素 class 不含固定高度（让 flex-1 工作）

### AC-5：间距合规

- layout 中所有 spacing class 都是 4 倍数（DESIGN.md principle）
- 不含 `p-1` `p-2` `p-3` `p-5` `p-7` `p-13` 等

### AC-6：错误路径

- layout 文件不存在 → 抛可读错误（vite-tsc / runtime）
- navItems 为空数组 → SideNav 渲染空（不崩）

---

## B3 测试矩阵

| 维度 | Case |
|---|---|
| **C6** | AC-1 三段 / AC-2 AppBar / AC-3 SideNav / AC-4 slot |
| **C7** | AC-3 navItems 字段 / AC-5 spacing 4 倍数 |
| **DOC** | AC-5 spacing 合规 = DESIGN.md principle |
| **ERR** | AC-6 layout 缺失抛错 |

**4 维度 / 6 case**

mock 占比 0%。

---

## B4 风险

| 风险 | 缓解 |
|---|---|
| 静态源码 regex 跟运行时 DOM 不一致 | 测试覆盖"结构特征"（class 名 / 元素标签），不测具体渲染 |
| navItems 改动频繁导致测试碎 | 测试断言只验证"必要字段"，不验证具体值 |
| `@nuxt/test-utils` SSR 测试复杂度高 | 阶段二再上，本 spec 仅源码断言 |

---

## B5 范围外

- T106 / T107 / T108 / T109 / T110（pages/* 单独 spec）
- T104（Pinia stores）
- T105（Nitro HTTP 端点）

---

## B6 工作量

- spec: 5 min
- 测试代码: 8 min
- audit + commit: 5 min
- **总计**: ~18 min