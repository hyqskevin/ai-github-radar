# T139 — 设置页合并初始化 + 配置回填修复 设计

> 状态：pending（待 TDD）
> 关联：docs/TODO.md T139
> 背景（真实复现帖单）：
> 1. 默认 `provider='none'` 时 settings.vue 用 `v-if` 隐藏 Model/API Key 输入框，用户看不到可配的 API key。
> 2. `loadConfig` 只拉 `/api/settings/llm`，`githubUser` 从不回填，进入设置页每次都是空。
> 3. `/init` 页与设置页重复，应合并入设置页，删除 `/init`。

## B1 设计

### 现状（已验证）

- 后端持久化正常：`GET/POST /api/settings/llm`、`GET/POST /api/settings/all` 均工作（`POST /api/settings/all` 已支持 `github_user` / `github_token`）。
- `frontend/app/pages/init.vue` 用 `POST /api/settings/all` 存 github + `POST /api/stars/refresh` 触发 init + 轮询 `/api/jobs`。

### 目标：设置页一站式管理

只用现前后端接口，纯前端改动。settings.vue 拆成三块：

1. **LLM card**（保留现有，修正 UX）
   - provider 下拉、model、api_key 输入。
   - 取消 `v-if` 把 API key 输入框藏起来的问题：`api_key` 输入框**始终渲染**（输入仅当填写时提交），避免"看不到 API key"。
   - 回填来自 `/api/settings/all`（含 `llm_provider` / `llm_model` / `llm_api_key_set`）。

2. **GitHub card**（init 并入）
   - username 输入：回填 `github_user`（修复空白）。
   - 新增 Personal Access Token 输入：POST `/api/settings/all` 存 `github_token`；只回显"已设置"标记(`github_token_set`)，不回显明文。
   - 提示 GITHUB_TOKEN 来自 .env 的可选性保留。

3. **初始化动作 card**（init 并入）
   - "保存并拉取 Star" 按钮：保存所有配置 → POST `/api/stars/refresh`(`user` + `no_llm`) → 轮询 `/api/jobs` 显示进度/结果（逻辑从 init.vue 迁入）。

### 删除

- 删除 `frontend/app/pages/init.vue`。
- `frontend/app/layouts/default.vue` navItems 移除 `{ label:'初始化', to:'/init' }`。
- 保留 `/api/settings/all`、`/api/settings/llm`、`/api/stars/refresh` 等后端和 Nitro 端点（init 页面删除不影响端点）。

## B2 验收（AC）

- AC-1：进入设置页，`githubUser` 回填真实值（非空），LLM provider/model 正确回显。
- AC-2：设置页存在 GitHub token 输入框，可保存 `github_token`；再次进入只提示已设置，不暴露明文。
- AC-3：设置页存在"拉取 Star"初始化动作，保存后触发 `/api/stars/refresh` 并轮询状态。
- AC-4：`init.vue` 文件与导航"初始化"项已移除；布局导航不再包含 `/init`。
- AC-5：API key 输入框不因 provider='none' 消失（始终渲染）。

## B3 测试矩阵

| 维度 | 断言 | 落点 |
|---|---|---|
| 前端 source | settings.vue 含 `githubUser` 回填 + `github_token` + `no_llm` + `/api/stars/refresh` + 轮询 | frontend/tests/unit/pages_more.test.ts |
| 前端 source | init.vue 文件不再存在；layout 无"初始化" | frontend/tests/unit/pages_more.test.ts |
| 后端回归 | `/api/settings/all` GET 返回 github_token 仅 `github_token_set`、不回明文 | tests/unit/web/test_app.py |
| 全量 | 后端 pytest + 前端 vitest 全绿 | 运行 CI |