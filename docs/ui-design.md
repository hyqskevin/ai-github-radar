# A4 UI 设计 — ai-github-radar

> Web dashboard 用 Nuxt 4 + Nuxt UI。设计 token 全部走 [DESIGN.md](../DESIGN.md)。

## 设计原则

1. **暗色优先** — 默认 `dark` 主题，自动跟随系统
2. **单一强调色** — `tertiary`（#4FD8EB）只用于 CTA / 链接 / 命中关键字
3. **4 倍数间距** — 所有间距 token 都是 4 的倍数
4. **WCAG AA** — 文本对比度 ≥ 4.5:1
5. **少即是多** — 不堆装饰，一个页面只一个 CTA

## 信息架构

### 路由表

| 路径 | 页面 | 主用途 |
|---|---|---|
| `/` | Dashboard | 今日推荐（默认页） |
| `/recommendations` | 推荐列表 | 历史推荐分页 / 搜索 / 筛选 |
| `/recommendations/:id` | 推荐详情 | 单条仓库详情 + 匹配关键字 |
| `/keywords` | 关键字管理 | 增删改 / 启停 / 来源（auto/manual） |
| `/stars` | 我的 star | 全量 star 列表 + 语言 / 主题分布图 |
| `/scan` | 扫描 | 手动触发 / 看历史扫描记录 |
| `/settings` | 设置 | 推送通道 / 周期频率 / Token |

### 全局布局

```
┌─────────────────────────────────────────────────────────┐
│  [LOGO] ai-github-radar           [theme] [health] [⚙]   │  ← AppBar
├──────┬──────────────────────────────────────────────────┤
│ Nav  │                                                  │
│ 📍   │                                                  │
│ 🏷   │             <Page Content>                         │
│ ⭐   │                                                  │
│ 🔄   │                                                  │
│ 📥   │                                                  │
│      │                                                  │
│ ⚙    │                                                  │
└──────┴──────────────────────────────────────────────────┘
```

- AppBar：`colors.neutral` 背景，高度 56px
- SideNav：240px 宽，可折叠到 64px（只留 icon）
- Content：max-width 1200px，居中

## 核心页面

### Dashboard `/`

- 顶部：今日推荐数量 + 上次扫描时间 + 健康状态
- 主区：推荐卡片网格（2 列桌面 / 1 列移动）
- 卡片内容：仓库名 / 描述 / ⭐ / 匹配关键字 chips / 时间 / "查看详情"按钮

```
┌─────────────────────────┐ ┌─────────────────────────┐
│ ⭐ 269,881              │ │ ⭐ 164,388              │
│ obra/superpowers        │ │ firecrawl/firecrawl    │
│                         │ │                         │
│ An agentic skills       │ │ The context API        │
│ framework...            │ │ to search, scrape...    │
│                         │ │                         │
│ [agent] [skill] [claude]│ │ [context] [scrape] [web]│
│                         │ │                         │
│ 2 hours ago             │ │ 3 hours ago             │
│             [详情 →]    │ │             [详情 →]    │
└─────────────────────────┘ └─────────────────────────┘
```

### 关键字管理 `/keywords`

- 表格：term / weight / source / enabled / 操作（启停 / 删 / 改权重）
- 顶部按钮：+ 新增关键字
- 筛选：按 source（auto/manual）/ 按 enabled

```
┌────────────────────────────────────────────────────────────┐
│ 关键字管理                                       [+ 新增]    │
├────────────────────────────────────────────────────────────┤
│ 筛选: [全部] [auto] [manual]              搜索: [______]   │
├────────────────────────────────────────────────────────────┤
│ term         │ weight │ source │ enabled │ 操作             │
├────────────────────────────────────────────────────────────┤
│ agent        │ 1.5    │ auto   │ ✓       │ [停] [改] [删]    │
│ claude code  │ 2.0    │ manual │ ✓       │ [停] [改] [删]    │
│ mcp          │ 1.2    │ auto   │ ✗       │ [启] [改] [删]    │
└────────────────────────────────────────────────────────────┘
```

### 扫描 `/scan`

- 顶部：手动触发按钮 + 配置（push target / limit）
- 主区：历史扫描记录表格（date / matched / pushed / channel / status）

## 组件清单（Nuxt UI 包装）

| 组件 | Nuxt UI 原生 | 我们的 wrapper |
|---|---|---|
| Button | `<UButton>` | `ButtonPrimary.vue`（套 DESIGN.md button-primary） |
| Card | `<UCard>` | `RepoCard.vue` |
| Input | `<UInput>` | `KeywordSearch.vue` |
| Chip | `<UBadge>` | `KeywordChip.vue`（命中 / 未命中两态） |
| Table | `<UTable>` | `KeywordsTable.vue` / `RecommendationsTable.vue` |
| Modal | `<UModal>` | — |
| Toast | `<UNotification>` | — |

## 状态管理（Pinia stores）

| Store | 状态 | 行为 |
|---|---|---|
| `useKeywordsStore` | `keywords[]` | fetch / add / update / remove / toggle |
| `useRecommendationsStore` | `recommendations[]` / pagination | fetch / refresh / filter |
| `useStarsStore` | `stars[]` / stats | fetch / refresh |
| `useScanStore` | `history[]` | trigger / fetch history |
| `useSettingsStore` | config snapshot | fetch / update |

每个 store 调 `$fetch('/api/...')`，不直接接 DB / GitHub。

## 国际化

阶段一**只支持 zh-CN**（你的母语）。i18n 文件 `app/web/i18n/zh-CN.ts`。A11 暂不启用，但保留目录结构（未来加 `en.ts`）。

## 测试覆盖

- [ ] `app/web/components/__tests__/` 每个组件一个 vitest
- [ ] `app/web/pages/__tests__/` 每个页面用 @nuxt/test-utils 跑 SSR 渲染
- [ ] `tests/e2e/web/` playwright 端到端：登录（无）→ 看推荐 → 加关键字 → 触发扫描
- [ ] DESIGN.md 每次改动跑 `npx -y @google/design.md lint` + `diff` 防回归

## 已知不做

- ❌ 主题切换 UI（固定暗色）
- ❌ 移动端优化（桌面优先）
- ❌ 拖拽排序
- ❌ 实时通知（轮询即可）