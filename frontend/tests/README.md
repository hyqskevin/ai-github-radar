# tests/

ai-github-radar 前端测试。

## 跑测试

```bash
# 一次性跑（CI 用）
pnpm test

# watch 模式（开发用）
pnpm test:watch

# 覆盖率
pnpm exec vitest run --coverage
```

## 目录

- `unit/` — 单元测试（vitest + happy-dom）
- `e2e/` — 端到端测试（playwright，本阶段未启用）

## 测试约定（8 步 loop §2）

- 测试先写 → 看到红 → 实现 → 看到绿 → 重构
- 每个 TODO 至少 1 个 unit + 1 个 e2e
- happy / edge / error 各 1 个 case
- mock 占比 ≤ 30%

详细 spec 见 `docs/superpowers/specs/`。