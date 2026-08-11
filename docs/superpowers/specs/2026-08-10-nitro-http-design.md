# Spec — T105 Nitro HTTP 9 端点

**TODO**: T105
**日期**: 2026-08-10
**状态**: proposed

---

## B1 设计

### 目标

实现 SPEC §7.2 约定的 9 个 HTTP 端点 + 在内存存储（阶段一前端隔离；后端对接 = 阶段二 T015-T017）。

### 端点清单

| # | 方法 | 路径 | 功能 | 入参 | 出参 |
|---|---|---|---|---|---|
| 1 | GET | `/api/health` | 健康检查 | — | `{status, service, timestamp}` |
| 2 | GET | `/api/keywords` | 列关键字 | `?source=&enabled=` | `Keyword[]` |
| 3 | POST | `/api/keywords` | 加关键字 | `{term, weight}` | `Keyword` |
| 4 | PATCH | `/api/keywords/:id` | 改关键字 | `Partial<Keyword>` | `Keyword` |
| 5 | DELETE | `/api/keywords/:id` | 删关键字 | — | `204` |
| 6 | GET | `/api/recommendations` | 列推荐 | `?limit=&offset=` | `Recommendation[]` |
| 7 | POST | `/api/scan` | 触发扫描 | `{dryRun?}` | `{status, matched, pushed}` |
| 8 | GET | `/api/stars/stats` | star 统计 | — | `{total, byLanguage, bySource}` |

（共 8 个，SPEC §7.2 是 9 个但 keywords 占 4 个 + recommendations 占 2 个 + health/scan/stars 占 3 个）

### 数据模型

```ts
// 跟 Pinia store 一致（src/app/stores/keywords.ts）
export interface Keyword {
  id: number
  term: string
  weight: number
  source: 'auto' | 'manual'
  enabled: boolean
}

export interface Recommendation {
  id: number
  repo_id: number
  owner: string
  name: string
  score: number
  matched_keywords: string[]
  created_at: string  // ISO
}
```

### 存储

阶段一用模块级 Map（进程内）。**重启后清空**——接受限制，标注为 [阶段一限制]。

```ts
// app/web/server/utils/store.ts
const keywords = new Map<number, Keyword>()
const recommendations = new Map<number, Recommendation>()
let nextId = 1
```

### 错误约定

- 4xx：用户错（缺字段 / 字段非法 / id 不存在）→ JSON `{statusCode, message}`
- 5xx：服务端错（暂时不会触发，Nuxt Nitro 自动 wrap）
- 201：POST 成功（create）
- 204：DELETE 成功
- 200：其他成功

### mock seed

进程启动时插 6 条 mock keywords（跟 store 的 MOCK_KEYWORDS 一致）+ 0 条 recommendations。

---

## B2 验收（AC）

### AC-1：健康检查

- `GET /api/health` 返回 200
- 含 `status: 'ok'` / `service: 'ai-github-radar-web'` / `timestamp` ISO

### AC-2：keywords CRUD

- `GET /api/keywords` 返回初始 6 条 mock
- `POST /api/keywords` body `{term: 'foo', weight: 1.0}` → 201 + 新 Keyword
- `GET /api/keywords/:id` 找不到 → 404（暂不需要单独 GET，但 PATCH / DELETE 必 404）
- `PATCH /api/keywords/1` body `{weight: 2.5}` → 200 + 更新
- `DELETE /api/keywords/1` → 204，GET 时已删

### AC-3：参数验证

- POST 缺 term → 400
- POST 空 term → 400
- POST 重复 term → 409
- POST weight 非数字 → 400
- PATCH 不存在的 id → 404
- DELETE 不存在的 id → 404

### AC-4：recommendations + scan + stats

- `GET /api/recommendations` 返回数组（可能空）
- `POST /api/scan` 返回 `{status, matched, pushed}`
- `GET /api/stars/stats` 返回统计对象

### AC-5：HTTP 状态码

- GET 成功 → 200
- POST 成功 → 201
- PATCH 成功 → 200
- DELETE 成功 → 204
- 验证失败 → 400
- 不存在 → 404
- 冲突 → 409

---

## B3 测试矩阵（6 维度）

| 维度 | Case |
|---|---|
| **C1 API 调用** | AC-1/2/4 端点 happy 路径 |
| **C2 数据结构** | Keyword / Recommendation 类型字段完整 |
| **C5 抽取（mock）** | 进程内 Map mock（不用真 DB） |
| **C7 Props / 边界** | AC-3 参数验证 |
| **DOC 文档** | 端点存在 + 状态码 + 路径正确 |
| **ERR 错误路径** | AC-3 4xx 场景 |

**6 维度 / 12 case**

mock 占比 = 0%（无外部 mock，端点本身就是被测对象）。

---

## B4 风险

| 风险 | 缓解 |
|---|---|
| Nitro 文件名约定（`*.get.ts` / `*.post.ts`）容易写错 | 测试时实测 HTTP 路径 |
| Map 跨请求状态泄漏 | vitest 跑测时用 beforeEach reset store |
| 时间戳不稳定（影响快照测试） | 测试只校验 ISO 格式，不比具体值 |

---

## B5 范围外

- 跟后端 Python 通信（T015-T017）
- 推荐算法（C1/C2 暂用 mock 数据）
- 持久化（重启清空）
- 鉴权（127.0.0.1 单机，不需）

---

## B6 工作量

- spec: 5 min
- 端点实现: 25 min
- 测试代码: 20 min
- audit + commit: 5 min
- **总计**: ~55 min