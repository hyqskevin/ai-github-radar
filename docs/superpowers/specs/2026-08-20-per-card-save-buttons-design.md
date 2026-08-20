# Spec: 设置页每卡片独立保存按钮

**日期**: 2026-08-20
**TODO**: T143
**类型**: 业务改进

---

## B1 设计

### 背景
- T142 之后,设置页 LLM 卡片有了「保存 LLM 配置」按钮
- GitHub 卡片没有自己的保存按钮 —— 用户填了 username/token 看不到保存入口
- 「保存配置 + 立即拉取」依赖 GitHub username,填了 username 也不一定能跑初始化(还要 token)
- 结果:用户配置 GitHub 后不知道在哪保存

### 改动

**1. 前端 app/pages/settings.vue**
- GitHub 卡片底部新增 `保存 GitHub 配置` 按钮(同 LLM 卡片的 primary 样式)
- 「保存配置 + 立即拉取」保留,但不再依赖 username 即可保存 —— 改为独立的「立即拉取」(只触发 init job,不重复保存)

### saveConfig 拆分为两段

保留现有 `saveConfig()`(全字段保存),卡片按钮调用同一个函数即可 —— 后端 `/api/settings/llm` POST 和 `/api/settings/all` POST 都是 idempotent,重复保存没问题。

### 用户体验
- LLM 卡片底部:`保存 LLM 配置`
- GitHub 卡片底部:`保存 GitHub 配置`
- 初始化卡片:`保存配置 + 立即拉取`(全字段保存 + 触发 init job)

---

## B2 验收 AC-N

- AC-1: 浏览器 `/settings` 页面 LLM 卡片 + GitHub 卡片**都**有 primary 保存按钮
- AC-2: 点 GitHub 保存按钮调用 `saveConfig()` 把 username/token 写 DB
- AC-3: 后端 `/settings/all` GET 返回最新 github_user/github_token_set
- AC-4: 前后端测试 + audit-loop 绿

---

## B3 测试矩阵 (C1-C10)

- C2 单元:`pages_more.test.ts` T125 断言 `保存 GitHub 配置` 字串存在
- C6 happy:浏览器 DOM 快照确认两按钮都 visible & enabled
- C8 错误:已 disabled 时按钮变灰不可点

不补 E2E(纯 UI 位置调整)。