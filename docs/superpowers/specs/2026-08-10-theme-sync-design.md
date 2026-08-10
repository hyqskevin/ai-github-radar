# Spec — T102 Theme 注入

**TODO**: T102
**日期**: 2026-08-10
**状态**: proposed

---

## B1 设计

### 目标

把 [DESIGN.md](../../DESIGN.md) 的 design token 自动注入 Nuxt UI 4 + Tailwind v4，**零硬编码颜色值**——所有颜色 / 间距 / 圆角 / 阴影走 DESIGN.md → app.config.ts / CSS 变量。

### 当前状态

- ✅ DESIGN.md 已写（colors / typography / spacing / rounded / elevation / components）
- ✅ app.config.ts 已声明 ui.colors（手填）
- ✅ main.css 已把 DESIGN.md 颜色映射成 Tailwind v4 `@theme static` CSS 变量
- ❌ **未自动化** — 改 DESIGN.md 要手改 app.config.ts + main.css（双源失同步风险）

### 目标架构

```
DESIGN.md (single source of truth)
       │
       ├──> app.config.ts (Nuxt UI primary palette name)
       │           └──> <UButton color="neutral"> 自动用对色
       │
       └──> app/assets/css/main.css (Tailwind v4 @theme static)
                   └──> --color-tertiary-400: #4FD8EB 等
```

**核心原则**：DESIGN.md 是**唯一**源。`pnpm theme:sync` 脚本从 DESIGN.md 重新生成 app.config.ts + main.css。CI 跑 `theme:lint` 检查两者一致。

### 自动化脚本

`scripts/theme-sync.mjs`（Node ESM，零依赖）：

1. 读 `DESIGN.md` 解析 YAML frontmatter
2. 提取 `colors` / `typography` / `spacing` / `rounded` / `elevation`
3. 生成 `app/web/app/app.config.ts`（覆盖 ui.colors 段）
4. 生成 `app/web/app/assets/css/main.css`（覆盖 @theme static 段）
5. 写回文件 + 报告变更

### 手动 vs 自动

| 场景 | 走哪条路 |
|---|---|
| 改 DESIGN.md token | `pnpm theme:sync` → 自动生成 |
| 改 UI 组件本身（不动 token） | 手改 .vue，token 不变 |
| 加新 token 类型 | 手改 DESIGN.md + 跑 `pnpm theme:sync` |

---

## B2 验收（AC）

### AC-1：sync 脚本能跑

- `node scripts/theme-sync.mjs` 退出码 0
- 第一次跑不报错（覆盖当前 app.config.ts + main.css）

### AC-2：生成的内容合法

- 生成的 `app.config.ts` 是合法 TS（vue-tsc 0 error）
- 生成的 `main.css` 是合法 CSS（Vite 编译无错）

### AC-3：颜色完整

- 所有 DESIGN.md `colors.*` 都映射到 main.css `--color-{name}-400/500/600` 三档（light/medium/dark）
- tertiary（强调色 #4FD8EB）必须暴露为 `--color-tertiary-400`（CSS 类 `text-tertiary-400` 可用）

### AC-4：脚本幂等

- 跑两次结果相同（不会每次加新行）
- DESIGN.md 不变时脚本输出无变化

### AC-5：lint 检查

- `node scripts/theme-sync.mjs --check` 检测源 vs 生成文件差异
- 不一致时退出码 1
- CI 阶段二（T113）集成

### AC-6：测试

- 7 个 it() case（按 12 维度矩阵 C2+C7+ERR 覆盖）
- 见 `docs/testing/c1-c10-matrix.md` T102 行

---

## B3 测试矩阵（6 维度）

| 维度 | Case |
|---|---|
| **C2 数据结构** | AC-3 验证 DESIGN.md colors → main.css 映射 |
| **C7 Props / 边界** | DESIGN.md 缺 colors / colors 为空 / 颜色非 hex |
| DOC 文档 | DESIGN.md 含 `colors.tertiary` |
| ERR 错误路径 | hex 非 `#xxxxxx` 格式 → 抛错而非静默 |
| ERR 错误路径 | 文件不存在 → 抛错 |

**最小门槛 3 维度**（happy/edge/error），实际覆盖 **5 维度 / 7 case**。

mock 占比 = 0%（无 mock）。

---

## B4 风险

| 风险 | 缓解 |
|---|---|
| DESIGN.md YAML 解析脆弱（regex 假设格式） | SPEC §C 锁死格式（design.md 规范），跑 `pnpm design:lint` 校验 |
| 生成文件被手改后 sync 覆盖丢失手改 | 脚本输出加 banner 注释"由 theme-sync 生成，请勿手改"；真要手改的拆 DESIGN.md |
| 脚本变 god object（既要解析又要生成） | 拆 `parse-design.mjs` + `generate-app-config.mjs` + `generate-main-css.mjs`，主脚本组合 |

---

## B5 范围外

- DESIGN.md 本身的 lint（用 google/design.md CLI，已加 `pnpm design:lint`）
- Tailwind theme.json 导出（design.md CLI 已支持，本 spec 不做）
- 其他 token 类型（motion / shadows 详细配置）— 阶段二再说

---

## B6 工作量

- spec: 5 min
- 测试代码: 10 min
- 脚本: 20 min
- 调试: 15 min
- **总计**: ~50 min