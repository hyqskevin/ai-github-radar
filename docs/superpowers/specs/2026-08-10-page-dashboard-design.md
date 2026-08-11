# Spec — T106 pages/index.vue 真实 Dashboard

**TODO**: T106
**日期**: 2026-08-10
**状态**: proposed

---

## B1 设计

### 目标

把 `app/web/app/pages/index.vue` 从 placeholder 升级为真实 Dashboard：
- 调 `useRecommendationsStore` 拉推荐
- 调 `useKeywordsStore` 拉关键字数
- 调 `useStarsStore` 拉 star 数（新建）
- 调 `useScanStore` 触发手动扫描（新建）
- 渲染真实数据 + 空状态 + 错误状态

### 现状

`app/web/app/pages/index.vue` 当前是 placeholder：
- 3 个 stat 卡片显示 `—`
- 一个空状态卡片 "脚手架已就绪"
- 引用 `T107/T108` 链接到 placeholder 页面

### 升级后结构

```
Dashboard (/)
├── Header
│   ├── <h1>Dashboard</h1>
│   └── <p>last updated description</p>
├── Stats Grid (3-4 stat cards)
│   ├── 今日推荐 (count from recommendations store)
│   ├── 启用关键字 (count from keywords store)
│   ├── 总 Star (count from stars store)
│   └── 上次扫描时间 (from scan store)
├── Action Bar
│   └── [扫描] button (trigger useScanStore)
├── Recommendations Grid
│   ├── 命中推荐 (top N = 6, score desc)
│   ├── 每个 RepoCard: owner/name/desc/score/matched_keywords chips/time
│   └── 空状态
└── Error Banner (if any store.error)
```

### 数据流

```ts
// onMounted
await Promise.all([
  recsStore.fetchAll(),
  keywordsStore.fetchAll(),
  starsStore.fetchStats(),
  scanStore.fetchHistory()
])
```

### 错误处理

- 任一 fetchAll 失败 → error banner 显示（store.error 已有）
- 不阻断其他 3 个（Promise.allSettled）
- 重试按钮触发对应 store 的 fetchAll

### 状态

| 阶段 | 显示 |
|---|---|
| loading（首次） | skeleton 占位 |
| 加载完成，有数据 | 真实数据 |
| 加载完成，空数据 | 空状态卡片（"还没有推荐"） |
| 加载失败 | 错误 banner + 重试按钮 |

### store 依赖

- `useRecommendationsStore`（T104 已有 store 文件，但 T105 endpoints 暴露 API）
  - **需要新建** `app/web/app/stores/recommendations.ts`（T105 endpoint 还没接 Pinia store）
- `useKeywordsStore`（T104 已有）
- **需要新建** `useStarsStore`（拉 `/api/stars/stats`）
- **需要新建** `useScanStore`（拉 `/api/scan` 历史 + 触发 scan）

新建 store 不在本 spec 范围（T107 范围）。**T106 只接已有 store，reco/stars/scan 用 mock 数据 fallback**。

---

## B2 验收（AC）

### AC-1：基础结构

- 页面包含 `<h1>Dashboard</h1>`
- 含 3 个 stat card（今日推荐 / 启用关键字 / 总 Star）
- 含推荐列表（≥ 0 卡片）
- 含 1 个 "扫描" 按钮

### AC-2：stat 数字

- stat 数字等于 store 的 items.length
- loading 时显示 `—`
- error 时显示 `?`

### AC-3：推荐列表

- 命中 store.items 渲染卡片
- 没数据时显示空状态
- 卡片按 score 降序
- 每张卡片有 owner/name/desc/score/matched_keywords

### AC-4：扫描按钮

- 点击触发 store 的 scanTrigger
- loading 时 disabled

### AC-5：错误恢复

- 任意 store.error 触发 banner
- banner 有重试按钮

### AC-6：DESIGN.md 合规

- 所有 spacing 走 4/8/16/24/32/48 token
- 用 tertiary 强调色

---

## B3 测试矩阵（5 维度）

| 维度 | Case |
|---|---|
| **C6 UI 渲染** | AC-1 5 个核心 element 存在 |
| **C7 Props / 边界** | 0 recommendations / loading / error 三态 |
| **C8 状态** | store 交互（扫描按钮触发 store）|
| **DOC** | DESIGN.md spacing + tertiary 颜色 |
| **ERR** | error banner 存在 + 重试 |

**5 维度 / 8 case**

mock 占比 ≤ 30%（mock 2-3 个 store 行为）

---

## B4 风险

| 风险 | 缓解 |
|---|---|
| recoms/stars/scan store 不存在 | 页面用 props 注入（页面接受 store 引用，测试 mock）|
| SSR 渲染跟 CSR 不一致 | happy-dom + 不依赖具体客户端 API |
| 真实 store 跟 T104 的 keywords store 风格不一致 | 复用 useKeywordsStore 模式 |

---

## B5 范围外

- T107 (pages/keywords.vue)
- T108 (pages/recommendations.vue)
- 新建 reco/stars/scan store（T107+ 范围）
- e2e playwright 测试

---

## B6 工作量

- spec: 5 min
- page 实现: 20 min
- 测试代码: 15 min
- audit + commit: 5 min
- **总计**: ~45 min