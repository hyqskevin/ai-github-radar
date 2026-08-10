# Spec — T101 Vitest Smoke Test

**TODO**: T101
**日期**: 2026-08-10
**作者**: hyqskevin
**状态**: proposed

---

## B1 设计

### 目标

为 ai-github-radar 前端（Nuxt 4）建立第一个单元测试，作为后续 T102-T112 的起点。验证：

1. 测试基础设施能跑（vitest 装好 + config 写好）
2. Nuxt UI 组件能 import + 渲染
3. 我们写的 layouts/default.vue 能被 Vitest + @nuxt/test-utils 加载
4. DESIGN.md 的"4 倍数间距"原则能用代码断言（防止后续回归）

### 选型

| 工具 | 用途 |
|---|---|
| vitest 2.1 | 单元测试 runner（项目已装） |
| happy-dom 15 | 浏览器环境（vitest environment） |
| @nuxt/test-utils 3.23 | Nuxt 组件渲染（仅在 e2e 用，本 spec 不依赖） |

### 测试范围

**in scope**：
- 1 个 unit test 文件 `app/web/tests/unit/smoke.test.ts`
- 3-5 个 it() cases（happy + edge + error 各 1 个，§C1-C10 覆盖：API mock / props / state）

**out of scope**：
- 组件快照测试（T104 之后才加）
- E2E（playwright，T108 之后）
- Python 后端测试（属于 T002-T015，单独 spec）

### 文件结构

```
app/web/
├── tests/
│   └── unit/
│       ├── smoke.test.ts        ← 本 spec 唯一产物
│       └── README.md             ← 跑测试说明
├── vitest.config.ts              ← 新增
```

---

## B2 验收（AC）

### AC-1：测试基础设施

- `pnpm test` 命令存在
- `vitest.config.ts` 在 `app/web/` 根目录
- happy-dom 环境配好

### AC-2：smoke test 跑通

- `pnpm test` 退出码 0
- 至少 3 个 it() 全 PASS
- happy / edge / error 各 1 个

### AC-3：实际测试内容

- [ ] AC-3.1 **happy**: Nuxt UI `<UCard>` 能在 happy-dom 渲染，DOM 含 `<div>` 节点
- [ ] AC-3.2 **edge**: 传入 props 为 `null` 时组件不崩（SPEC 错误路径 §C4）
- [ ] AC-3.3 **error**: 4 倍数间距 token 集合里不含 13 / 17 等奇数（防止 DESIGN.md token 漂移）

### AC-4：覆盖率

- 覆盖率报告生成（`pnpm test --coverage`）
- 阶段一覆盖率目标 ≥ 80%（整个项目，不是单 spec）

### AC-5：CI 集成（阶段一可选）

- 不在本 spec 范围（T113 阶段二做 CI）

---

## B3 测试矩阵（C1-C10 维度）

按 agent-loop-scaffold §2 硬规则，每个 TODO 至少 1 个 unit + 1 个 e2e；mock 占比 ≤ 30%。

| 维度 | 是否覆盖 | 备注 |
|---|---|---|
| C1 API 调用 | ❌ | 本 spec 无 API |
| C2 数据结构 | ⚠️ | spacing tokens（AC-3.3） |
| C3 SEC / 权限 | ❌ | 阶段一单人单机 |
| C4 异步 / 队列 | ❌ | 本 spec 无异步 |
| C5 抽取（mock） | ❌ | 本 spec 无外部依赖 |
| C6 UI 渲染 | ✅ | AC-3.1 UCard |
| C7 Props / 边界 | ✅ | AC-3.2 null props |
| C8 状态 | ❌ | 本 spec 无 store |
| C9 E2E | ❌ | 本 spec 仅 unit |
| C10 性能 | ❌ | 本 spec 无 perf |

**mock 占比**: 0%（无 mock）— 严格符合 §2 ≤ 30%。

**错误路径**: AC-3.2（null props）+ AC-3.3（不变量）— 各 1 个。

---

## B4 风险

| 风险 | 缓解 |
|---|---|
| vitest + Nuxt 4 兼容性问题（@nuxt/test-utils 还在 beta） | 不在 spec 内用 @nuxt/test-utils；纯 vitest + happy-dom 足够 smoke |
| happy-dom 与 Nuxt UI 4 SSR 渲染不一致 | smoke 只测 DOM 节点存在，不测精确 HTML |
| Vue 3 单文件组件 .vue 需要额外 loader | vitest 配 `@vue/compiler-sfc` 处理 |

---

## B5 范围外

- T102（theme 注入测试）
- T103（layout 完整测试）
- T104（Pinia store 测试）
- T113（CI 集成）
- Python 后端任何测试

---

## B6 工作量

- spec 写：5 min
- 测试代码：5 min
- vitest 配置：3 min
- 跑通 + 修：10 min
- 验证：2 min
- **总计**: ~25 min