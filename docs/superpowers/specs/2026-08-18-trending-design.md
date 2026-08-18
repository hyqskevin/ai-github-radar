# Spec — T005 github/trending.py (待 T005 会话补全)

> 占位 spec。下次会话第一件事:补 B1 设计(HTML 解析 vs search API fallback)/
> B2 AC(fetch trending ≥ 20 条)/ B3 测试矩阵。

## 上下文

- SPEC.md §3 / §6：trending 数据源是 GitHub Trending HTML + search API 兜底
- docs/TODO.md T005 AC：scan 能拿到当天 trending ≥ 20 条
- 阶段一硬约束:零成本,不引第三方 trending 包(README.md §技术选型说用 `gh-trending` PyPI,但 ADR 应明确放弃,改用自实现 HTML 解析 + search API 兜底)

## 决策点(下次会话第一句问用户)

1. **HTML 解析器**：beautifulsoup4(已装,慢但稳) vs selectolax(更快,需新装)
2. **fallback 触发条件**：HTML 解析失败?response 非 200?两种都触发?
3. **每日 quota**：search API 30 req/min,默认一天拉 1 次就够,但要不要 retry?