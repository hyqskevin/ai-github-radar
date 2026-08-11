# Spec — T104 Pinia keywords store

**TODO**: T104
**日期**: 2026-08-10
**状态**: proposed

---

## B1 设计

### 目标

建 `app/web/app/stores/keywords.ts`（Pinia store）：
- 管理关键字 CRUD（增 / 删 / 改 / 启停）
- 调 Nuxt Nitro `server/api/keywords` 端点
- 暴露给 `pages/keywords.vue`（T107 用）

### Store API

```ts
interface Keyword {
  id: number
  term: string
  weight: number
  source: 'auto' | 'manual'
  enabled: boolean
}

interface KeywordsState {
  items: Keyword[]
  loading: boolean
  error: string | null
}

useKeywordsStore() {
  // state
  items: Keyword[]
  loading: boolean
  error: string | null

  // getters
  enabledItems: Keyword[]
  bySource: Record<'auto' | 'manual', Keyword[]>

  // actions
  fetchAll(): Promise<void>
  add(term: string, weight?: number): Promise<Keyword>
  update(id: number, patch: Partial<Keyword>): Promise<Keyword>
  toggle(id: number): Promise<Keyword>
  remove(id: number): Promise<void>
  $reset(): void
}
```

### HTTP 端点映射

| action | method | path |
|---|---|---|
| `fetchAll` | GET | `/api/keywords` |
| `add` | POST | `/api/keywords` |
| `update` | PATCH | `/api/keywords/:id` |
| `toggle` | PATCH | `/api/keywords/:id` + `{enabled: !current}` |
| `remove` | DELETE | `/api/keywords/:id` |

**注意**：阶段一前端**只有 mock 数据**（server/api 没真后端对接 Python），所以 store 内部 fetch 会 catch 404 并回退到 mock seed。

### Mock seed（fetch 失败时用）

```ts
const MOCK_KEYWORDS: Keyword[] = [
  { id: 1, term: 'agent', weight: 1.5, source: 'auto', enabled: true },
  { id: 2, term: 'claude code', weight: 2.0, source: 'manual', enabled: true },
  { id: 3, term: 'mcp', weight: 1.2, source: 'auto', enabled: false },
  { id: 4, term: 'rust', weight: 0.8, source: 'manual', enabled: true },
  { id: 5, term: 'nuxt', weight: 1.0, source: 'auto', enabled: true },
  { id: 6, term: 'typescript', weight: 1.3, source: 'manual', enabled: false },
]
```

### 状态语义

- `loading` 在 fetchAll 开始时 true，结束（成功/失败）后 false
- `error` 在 HTTP 4xx/5xx 或网络错误时设，store 仍保留旧 items（不覆盖）
- `add` 成功后把新 Keyword push 到 items 末尾
- `remove` 成功后从 items 过滤掉 id

### 防御

- `add` 时 trim + 拒绝空字符串 + 拒绝重复 term
- `update` 时若 id 不存在抛 Error
- `remove` 同样校验

---

## B2 验收（AC）

### AC-1：基础 CRUD

- store 初始 `items=[]` `loading=false` `error=null`
- `fetchAll()` 加载 6 条 mock seed
- `add('foo')` 返回 Keyword + items 长度 +1
- `update(1, { weight: 2.5 })` 修改 weight
- `remove(1)` items 长度 -1
- `toggle(2)` 翻转 enabled

### AC-2：getters

- `enabledItems` 只含 enabled=true
- `bySource.auto` 只含 source='auto'
- `bySource.manual` 只含 source='manual'

### AC-3：状态管理

- 重复 add 同一 term 抛 Error
- update 不存在的 id 抛 Error
- remove 不存在的 id 抛 Error
- add 空字符串 / 纯空白抛 Error

### AC-4：fetch 错误路径

- `fetchAll()` 在 HTTP 404 时回退到 mock seed + error='Using mock data'

### AC-5：reset

- `$reset()` 清空 items + loading=false + error=null

---

## B3 测试矩阵（7 维度）

| 维度 | Case |
|---|---|
| **C1 API 调用** | AC-4 fetch 错误回退 |
| **C2 数据结构** | AC-2 getters 类型断言 |
| **C4 异步 / 队列** | fetchAll loading 状态 |
| **C5 抽取（mock）** | mock fetchAll / mock $fetch |
| **C8 状态** | AC-1 CRUD / AC-3 错误防御 / AC-5 reset |
| **DOC 文档** | store 文件存在 + 类型导出 |
| **ERR 错误路径** | AC-3 重复 / 不存在 / 空 |

**7 维度 / 8 case**

mock 占比 ≤ 30%（只用 1-2 个 mock，其他走真实 Pinia）。

---

## B4 风险

| 风险 | 缓解 |
|---|---|
| Pinia + Nuxt 4 SSR hydration 不一致 | store 用 `defineStore` 标准 API，加 `pinia-plugin-persistedstate` 在阶段二 |
| $fetch mock 在 vitest 里失效 | 用 `vi.mock('#app', () => ({ $fetch: vi.fn() }))` |
| store import 循环 | store 只 import types + `#app` 的 $fetch |

---

## B5 范围外

- 关键字搜索 / 过滤（UI 在 T107）
- 关键字聚类（阶段二 LLM 升级）
- 后端 Python 实现（T104 只做前端 store；后端 = T015-T017）

---

## B6 工作量

- spec: 8 min
- store 代码: 15 min
- 测试代码: 15 min
- audit + commit: 5 min
- **总计**: ~45 min