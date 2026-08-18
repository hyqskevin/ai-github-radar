# Spec — T002 config.py

| 维度 | 内容 |
|---|---|
| **TODO ID** | T002（docs/TODO.md §基础设施） |
| **作者** | ai-github-radar 维护者 + AI 助手（2026-08-18） |
| **优先级** | 高 — 所有 T003+ 都依赖配置加载 |
| **触发** | docs/TODO.md T002 + docs/api-doc.md §config |

---

## B1. 设计

### 1.1 目标

实现 `src/ai_github_radar/config.py`：
- Pydantic Settings v2 加载 `.env`（默认 `./config/.env`，可由 `RADAR_CONFIG_PATH` 覆盖）
- 强类型字段：GitHub token / Radar 用户 / 推送 target / 抓取 interval / DB URL / LLM API keys（可选）
- 提供 `validate_config()` 函数：跑 Pydantic 校验，配置不对抛 `ConfigError` 并打印具体哪条字段错
- 提供 `load_settings()` 缓存函数（functools.lru_cache 或 Pydantic 自带 .env_file 加载）
- 提供 `__main__` 入口支持 `python -m ai_github_radar.config --validate`（最小可用 CLI，等 T012 完整 CLI 前置）

### 1.2 字段定义

| 字段 | 类型 | 默认 | 必填 | 说明 |
|---|---|---|---|---|
| `github_token` | str | 无 | 是 | GitHub PAT，scope: public_repo |
| `radar_user` | str | 无 | 是 | GitHub username |
| `radar_fetch_interval` | Literal["daily","weekly"] | "daily" | 否 | |
| `radar_push_target` | Literal["local","feishu","email"] | "local" | 否 | |
| `db_url` | str | "sqlite:///./data/radar.db" | 否 | SQLAlchemy URL |
| `feishu_webhook_url` | HttpUrl \| None | None | 否 | 配 push=feishu 时必填 |
| `smtp_host` | str \| None | None | 否 | 配 push=email 时必填 |
| `smtp_port` | int \| None | None | 否 | |
| `smtp_user` | str \| None | None | 否 | |
| `smtp_password` | SecretStr \| None | None | 否 | |
| `smtp_to` | str \| None | None | 否 | 收件人邮箱 |
| `openai_api_key` | SecretStr \| None | None | 否 | LLM 升级用 |
| `anthropic_api_key` | SecretStr \| None | None | 否 | LLM 升级用 |

### 1.3 跨字段校验（model_validator）

- `radar_push_target == "feishu"` 时 `feishu_webhook_url` 必填
- `radar_push_target == "email"` 时 `smtp_host / smtp_port / smtp_user / smtp_password / smtp_to` 必填
- 两者同时配也可（共存），不强排他

### 1.4 非目标

- ❌ 不建 CLI 子命令（仅 `__main__` 最小入口）；完整 CLI T012
- ❌ 不暴露加密存储（明文 .env，依赖 OS 文件权限）
- ❌ 不做配置热重载（reload 由 daemon 重启完成）

### 1.5 错误约定

- 缺必填字段 → `ConfigError`，stdout 字段名 + 期望类型 + 实际值（隐藏 token）
- token 字段任何时候不在 stdout 显示完整值（即使是错误信息）

---

## B2. 验收（AC-N）

| AC | 断言 | 怎么验 |
|---|---|---|
| AC-1 | 合法 .env 下 `python -m ai_github_radar.config --validate` 退出码 0 + stdout 含 "OK" | 跑命令看 echo $? = 0 + stdout 含 OK |
| AC-2 | 缺 GITHUB_TOKEN 时报具体错 | .env 删 GITHUB_TOKEN → exit 2 + stdout 含 "github_token" |
| AC-3 | `radar_push_target=feishu` 但缺 webhook → 报字段名 | .env 配 RADAR_PUSH_TARGET=feishu + 无 FEISHU_WEBHOOK_URL → exit 2 + stdout 含 "feishu_webhook_url" |
| AC-4 | `load_settings()` 返回 Settings 单例（lru_cache 命中） | 单测：连续调用 id() 相等 |
| AC-5 | SecretStr 字段不在 `repr` / `print` 出现明文 | 单测：`repr(settings.openai_api_key)` 不含真实 key |
| AC-6 | 错误信息不打印 token 明文 | 单测：故意让 smtp_password 校验失败，stdout 不含 key 值 |

---

## B3. 测试矩阵

| C | 维度 | 覆盖 |
|---|---|---|
| C1 功能 | 合法配置加载 | AC-1 |
| C2 功能 | 必填字段缺失 | AC-2 |
| C3 功能 | 跨字段依赖校验 | AC-3 |
| C4 边界 | load_settings 单例 | AC-4 |
| C5 边界 | SecretStr 不暴露明文 | AC-5 |
| C6 错误 | token 错误信息脱敏 | AC-6 |
| C7 错误 | radar_user 含特殊字符仍接受（GitHub username 规则放宽） | 单测："hyqskevin" + "user-name_1" 均通过 |
| C8 边界 | 字段名解析大小写不敏感 | 单测：.env 写 `github_token` 或 `GITHUB_TOKEN` 都识别 |
| C9 一致性 | 默认值与 SPEC.md §3 一致 | 单测：不写 RADAR_FETCH_INTERVAL 时 = "daily" |
| C10 错误 | .env 文件不存在 | 单测：抛 ConfigError 提示路径 |

测试文件：`tests/unit/test_config.py`

---

## B4. 风险

- **R1**：Pydantic Settings v2 与 v1 API 差异大，PyGithub 已用 v1 风格代码。**缓解**：T002 严格用 v2 API（model_config + `@field_validator` + `model_validator` mode="after"）。
- **R2**：宿主机 Python 是 3.9，pyproject 标 requires-python = ">=3.12"。**缓解**：CI / uv 环境必须 3.12；本会话宿主机跑测试仅作冒烟，AC-1 验证用 `python3 -m ai_github_radar.config`。
- **R3**：跨字段校验失败时 Pydantic v2 抛 ValidationError，子进程测试 stderr 抓取容易丢字段名。**缓解**：错误信息固定格式 `field: <name>; reason: <msg>`，断言靠关键字包含。