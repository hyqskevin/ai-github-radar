# Spec: 设置页新增 LLM Base URL 字段 + 后端持久化

**日期**: 2026-08-20
**TODO**: T142
**类型**: 业务功能

---

## B1 设计

### 背景
- 后端 `summarizer._ResolvedLLM.base_url` 已存在，但 `services/settings.py` 没存该值
- `/api/settings/llm` POST 不接受 `base_url`
- 前端 settings.vue 无 base_url 输入框
- 结果：用户填 MiniMax / Qwen 自建网关 / Azure OpenAI 等非默认 OpenAI 兼容端点时，**无法在 UI 配置 API URL**；系统仍走 provider 默认 base_url，导致调用失败

### 改动

**1. 后端 services/settings.py**
- 新增常量 `KEY_LLM_BASE_URL = "llm.base_url"`

**2. 后端 web/app.py**
- `api_get_llm_settings` 多读 `KEY_LLM_BASE_URL`，返回 `base_url`
- `api_set_llm_settings` 接受 `body["base_url"]`（None 不动）
- `api_get_all_settings` 多读 `KEY_LLM_BASE_URL`，返回 `llm_base_url`

**3. 后端 llm/summarizer.py**
- `_resolve_llm_from_db_settings` 多读 `KEY_LLM_BASE_URL`，传入 `_ResolvedLLM.base_url`

**4. 前端 app/pages/settings.vue**
- `config` 增加 `llmBaseUrl: ''`
- loadConfig 从 `/api/settings/all` 读 `llm_base_url` 回填
- saveConfig 给 `/api/settings/llm` body 带 `base_url`
- 模板新增 Base URL `UInput` 字段（位于 Provider 和 Model 之间）
  - placeholder: `例:https://api.minimax.chat/v1`
  - help: "OpenAI 兼容 API 地址;留空走 provider 默认"
- 仅在 `llmProvider && llmProvider !== 'none'` 时显示

---

## B2 验收 AC-N

- AC-1: 后端 `test_app.py` 新增测试 `test_api_settings_llm_with_base_url_roundtrip` —— POST `{provider, model, api_key, base_url}` 后 GET 返回对应 base_url
- AC-2: 后端 `test_app.py` 验证 `/settings/all` 返回 `llm_base_url`
- AC-3: 前端 `pages_more.test.ts` T125 用例增加断言：`settings.vue` 包含 `config.llmBaseUrl` 和 `llmBaseUrl`
- AC-4: 浏览器实际打开 `/settings`，Base URL 输入框存在且可填（minimax 之类）
- AC-5: audit-loop L0 + 前后端 pytest 全绿

---

## B3 测试矩阵 (C1-C10)

- C2 单元：test_app.py roundtrip 测试覆盖 base_url 写入/读取
- C6 happy：前端 Base URL 输入存在；后端读取返回
- C7 edge：base_url 为空字符串视为未设置（保留 provider 默认）
- C8 错误路径：填了无效 base_url 不应崩溃（最终调用失败由 LLM SDK 抛错）

不补 E2E（无 UI 流程变化，仅加一个字段）。