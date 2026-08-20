# Spec: 修复 frontend/tests/unit/layout.test.ts 路径 bug

**日期**: 2026-08-20
**TODO**: T141
**类型**: FIXUP / 路径修正

---

## B1 设计

### 问题
`frontend/tests/unit/layout.test.ts` 中 `REPO_ROOT` 计算结果错误：

```ts
// 当前（错误）：
const REPO_ROOT = resolve(__dirname, '../../../..')
const LAYOUT_PATH = join(REPO_ROOT, 'frontend/app/layouts/default.vue')
```

- `__dirname` = `frontend/tests/unit`
- `../../../..` 从 `frontend/tests/unit` 向上 4 级 → `/Users/kevin_w/Documents/github`
- 拼上 `frontend/app/layouts/default.vue` → `/Users/kevin_w/Documents/github/frontend/app/layouts/default.vue`（**少一级 `ai-github-radar`**）

### 修复
- `frontend/tests/unit` 向上 3 级到 repo root → `../../..`
- 拼上 `frontend/app/layouts/default.vue` 即可

```ts
const REPO_ROOT = resolve(__dirname, '../../..')
const LAYOUT_PATH = join(REPO_ROOT, 'frontend/app/layouts/default.vue')
```

---

## B2 验收 AC-N

- AC-1: `cd frontend && pnpm vitest run tests/unit/layout.test.ts` 全部 7 个用例通过
- AC-2: git diff 仅修改 `frontend/tests/unit/layout.test.ts` 的 REPO_ROOT/LAYOUT_PATH 两行
- AC-3: commit message 遵循 AGENTS.md §7: `TODO(T141): fix layout.test.ts REPO_ROOT path`

---

## B3 测试矩阵 (C1-C10)

- C2 单元 (静态断言)：本文件本身就是源文件断言测试，路径修复后自动覆盖
- C6 happy：执行 `pnpm vitest run tests/unit/layout.test.ts` 7 测试全绿
- C7 edge：路径在 monorepo 任意 cwd 下应解析正确（vitest 运行 cwd = frontend/，与生产 CI 一致）

不补 E2E（纯路径常量修复，无新功能）。