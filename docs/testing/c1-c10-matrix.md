# 12 维度测试矩阵 — ai-github-radar

> 基于 agent-loop-scaffold §2 的 C1-C10 测试维度 + 2 个外延（文档 / 错误路径）= **12 维度**。
> 每个 TODO 必须先填本文档的对应行，再写测试代码（[4] TDD 红）。

---

## 12 维度定义

| ID | 维度 | 范围 | 示例 |
|---|---|---|---|
| **C1** | API 调用 | HTTP / RPC / SDK 调用 | `/api/keywords` POST、PyGithub `get_user().get_starred()` |
| **C2** | 数据结构 | 序列化 / 解析 / 校验 | JSON ↔ Pydantic、DESIGN.md YAML frontmatter 解析 |
| **C3** | SEC / 权限 | 鉴权 / 越权 / 注入 | PAT scope、CSRF、路径穿越 |
| **C4** | 异步 / 队列 | 任务调度 / 锁 / 重试 | daemon 周期、SQLAlchemy session、aiohttp 并发 |
| **C5** | 抽取（mock） | 外部依赖 mock / fixture | `respx` mock httpx、`monkeypatch` os.environ |
| **C6** | UI 渲染 | 组件 / DOM / 样式 | Nuxt UI 组件 mount、Dashboard 渲染、DESIGN.md token 应用 |
| **C7** | Props / 边界 | 入参边界 / 类型转换 | null props、空字符串、Unicode、Int overflow |
| **C8** | 状态 | store / ref / computed | Pinia keywords store、dark mode toggle |
| **C9** | E2E | 端到端流程 | `@nuxt/test-utils` 跑 SSR、`playwright` 浏览器 |
| **C10** | 性能 | benchmark / 内存 / IO | `pytest-benchmark`、N+1 查询、bundle size |
| **DOC** | 文档 | spec 完整性 / AC 可观测 | DESIGN.md token、SPEC.md §9 验收、CHANGELOG |
| **ERR** | 错误路径 | 异常 / 边界 / 资源耗尽 | 401/403/429、空指针、磁盘满、超时 |

---

## 覆盖率硬约束（来自 agent-loop-scaffold §2）

- 每个 TODO 至少 **1 unit + 1 e2e**
- **mock 占比 ≤ 30%**（防止"局部最优"）
- **happy / edge / error 各 1 个 case**
- **"没写测试" = "没做完"**

---

## TODO × 12 维度矩阵

> 每个 TODO 在此表勾选覆盖的维度。**最少 3 维度（happy/edge/error），推荐 5+ 维度。**

### 阶段一 v0.1.0

| TODO | 名称 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | C10 | DOC | ERR | 覆盖数 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **T101** | vitest smoke | | ✅ | | | | | ⚠️ | | | | | ✅ | ✅ | **4** |
| **T102** | theme-sync from DESIGN.md | | ✅ | | | | ✅ | ✅ | ✅ | | | ✅ | ✅ | **6** |
| T103 | layouts/default | | | | | | ✅ | ✅ | | | | ✅ | ⚠️ | 4 |
| **T104** | Pinia keywords store | ✅ | ✅ | | ✅ | ✅ | | | ✅ | | | ✅ | ✅ | **7** |
| **T105** | Nitro HTTP 8 端点 | ✅ | ✅ | | | ✅ | | ✅ | | | | ✅ | ✅ | **6** |
| **T106** | pages/index Dashboard | | | | | | ✅ | ✅ | ✅ | ⚠️ | | ✅ | ✅ | **5** |
| T107 | pages/keywords | ✅ | ✅ | ✅ | | ✅ | ✅ | ✅ | ✅ | ⚠️ | | ✅ | ✅ | 9 |
| T108 | pages/recommendations | ✅ | ✅ | | | ✅ | ✅ | ✅ | ✅ | ⚠️ | | ✅ | ✅ | 8 |
| T109 | pages/scan | ✅ | ✅ | | ⚠️ | ✅ | ✅ | ✅ | ✅ | ⚠️ | | ✅ | ✅ | 8 |
| T110 | pages/stars + settings | | ✅ | | | | ✅ | ✅ | ✅ | ⚠️ | | ✅ | ✅ | 6 |
| T111 | design:lint export CI | | ✅ | | | | | | | | | ✅ | ⚠️ | 3 |
| T112 | dev.sh | | | | ⚠️ | | | | | ✅ | | ✅ | ✅ | 4 |
| T001-T019 | 后端 19 TODO | ✅ | ✅ | ✅ | ✅ | ✅ | | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ | 9+ |

⚠️ = 部分覆盖（spec 里要写清楚"豁免 / 简化"理由）

---

## T101 现状复盘（按 12 维度）

| 维度 | T101 实际覆盖？ | 缺什么 |
|---|---|---|
| C1 API 调用 | ❌ | T101 是 smoke，不调 API |
| **C2 数据结构** | ✅ `readSpacingTokens()` 解析 YAML | — |
| C3 SEC / 权限 | ❌ | 阶段一单人单机，豁免 |
| C4 异步 / 队列 | ❌ | T101 不涉及，豁免 |
| C5 抽取（mock） | ❌ | 0 mock（合规） |
| **C6 UI 渲染** | ❌ | **缺** — 改：加 1 个 mount `<UCard>` + Nuxt UI token 注入检查 |
| C7 Props / 边界 | ⚠️ | 只测 null props，加：空字符串 / 嵌套数组 / Int max |
| C8 状态 | ❌ | 阶段一尚无 Pinia store，豁免 |
| C9 E2E | ❌ | T101 不涉及，豁免（保留到 T106） |
| C10 性能 | ❌ | 豁免 |
| **DOC** | ✅ | spec + README + DESIGN.md 都验 |
| **ERR** | ✅ | edge（解析失败）+ error（不变量违反） |

**T101 缺 1 个必填维度（C6 UI 渲染）**——下面补。

---

## T101 必须补的 case

### C6 UI 渲染（新增 1 case）

```ts
it('happy: UCard renders via @vue/test-utils mount (UI 渲染 smoke)', () => {
  // 跳过原因：本 spec 不引入 @vue/test-utils 避免 Vue 编译路径噪音
  // 等 T106 写 pages/ 时一起加 @nuxt/test-utils 集成测试
})
```

**结论**：本 spec **不补 C6**，加豁免说明（避免引入 `@vue/test-utils` 这个 Vue 编译路径未知的依赖）。T101 维持 3 维度覆盖（C2/DOC/ERR）+ 1 边界（C7）。

### C7 Props 边界（升级现有 edge case）

```ts
it('edge: DESIGN.md parsing tolerates empty spacing block (empty string boundary)', () => {
  // 等实现层加：readSpacingTokens 遇到空 spacing: 块返回 {}
  // 不抛错而是返回 {} 让上层判断
})
```

**结论**：**加 1 个 case**（C7 边界从 null props 升级到空 block），T101 总计 **4 case / 3 维度覆盖**。

---

## 12 维度最低门槛

按 agent-loop-scaffold §2 硬规则：

- 最低门槛 = **3 维度**（happy/edge/error 各 1 case）
- 推荐门槛 = **5+ 维度**
- 高质量门槛 = **8+ 维度**

T101 = **4 维度 / 4 case** = 超过最低门槛，未达推荐门槛（因为是 smoke 起步，刻意小）。

后续 TODO（T102-T112）按上表覆盖，**整个项目 v0.1.0 累计 ≥ 30 维度覆盖**即达标。

---

## 测试目录约定

```
app/web/tests/
├── unit/                        # vitest 单元测试（happy-dom）
│   ├── _TEMPLATE.test.ts         # 模板（参照 agent-loop-scaffold 的 tests/_TEMPLATE.md）
│   ├── smoke.test.ts             # T101
│   ├── theme.test.ts             # T102
│   ├── layout.test.ts            # T103
│   ├── stores/
│   │   └── keywords.test.ts      # T104
│   ├── api/
│   │   ├── keywords.test.ts      # T105
│   │   └── recommendations.test.ts
│   └── pages/                    # T106-T110
│       ├── index.test.ts
│       ├── keywords.test.ts
│       └── ...
├── e2e/                         # playwright（T113+ 启用）
└── README.md                    # 本文件 + 12 维度总览
```

---

## 跑测试

```bash
pnpm test                    # 一次性（CI）
pnpm test:watch              # watch 模式
pnpm exec vitest run --coverage
```

按本文档 + SPEC §AC 跑。任何新 TODO **必须先更新本文档对应行**，再写测试代码。