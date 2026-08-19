# T138 — star 列表分页 设计

> 状态：pending（待 TDD）
> 关联：docs/TODO.md T138
> 背景：stars.vue 一次 `useFetch('/api/stars')` 拉全部（limit 默认 200），无分页 UI；后端 `/api/stars` 已支持 limit/offset 但缺 `total`，前端无法算总页数。

## B1 设计

### 后端契约 `/api/stars`（GET）

沿用现有路由，响应新增 `total` 字段（不做破坏性修改）：

```json
{
  "stars": [...],
  "limit": 20,
  "offset": 0,
  "total": 137
}
```

- `total` = stars 表未过滤总行数（当前无过滤条件，直接 count）。
- `limit`：服务端默认上限仍为 200；前端显式传 20。
- `offset`：翻页游标。
- 排序保持现状：`starred_at desc nullslast, id desc`。

### 前端 stars.vue

- `useFetch('/api/stars')` 传 `query: { limit: 20, offset }`（offset 为响应式）。
- 用新增 `total` 计算总页数。
- 采用 Nuxt UI `UPagination`（非 deprecated 组件）渲染分页，`v-model` 当前页 → 换算 offset。
- 醒目列出导航：上一页 / 下一页 / 页码。
- 空态与统计卡片逻辑不变。

### 边界与默认

- `limit` 前端固定 20（合理一屏）；后端保留可覆盖。
- DB 无 star 时 `total = 0`，分页组件隐藏，维持"还没有 star 数据"空态。
- 翻页不清空统计区（统计走独立 `/api/stars/stats` 请求）。

## B2 验收（AC）

- AC-1：`GET /api/stars?limit=2&offset=0` 返回 `stars` 长度 ≤ 2，且 `total` 为表内总条数。
- AC-2：`offset` 生效——第二页数据不与第一页重叠（用例聚焦 LIMIT/OFFSET + total 数学一致）。
- AC-3：stars.vue 使用 `UPagination` 且读取响应 `total` 计算页数、传 `offset` 请求。
- AC-4：`total = 0` 时前端保持空态文案，不渲染分页错误。

## B3 测试矩阵

| 维度 | 断言 | 落点 |
|---|---|---|
| 后端 happy | 3 条记录 limit=2 offset=0 → 2 条 + total=3 | tests/unit/web/test_app.py |
| 后端 offset | 3 条记录 offset=2 → 第 3 条 | tests/unit/web/test_app.py |
| 后端空 | 0 条记录 → stars=[], total=0 | tests/unit/web/test_app.py |
| 前端集成 | stars.vue 含 `UPagination`、`total`、`offset` | frontend/tests/unit/pages_more.test.ts |
| 前端契约 | index.get.ts 透传 limit/offset（现有，验证未回归） | 运行既有 frontend vitest |