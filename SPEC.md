# SPEC.md — ai-github-radar 项目设计

> **本文件是项目级设计文档 A1 维度**。按 AGENTS.md §0 loop [1] 文档前置阶段必填。
> 9 段缺一不可,audit-loop L0 校验。新项目 init 后第一步是填实本文件。

---

## 1. 目标

为已经有一定 GitHub star 收藏的开发者（≥ 30 个），自动从 star 历史建模技术偏好 → 提取关键字 → 定期扫描 GitHub Trending / search API → 推送匹配关键字的新项目到本地 / 飞书 / 邮件。

阶段一交付：
- CLI：`init`（拉 star + 提取关键字）、`scan`（单次扫描 + 推送）、`daemon`（周期守护）
- 配置文件 `.env` + YAML 关键字订阅
- 本地 SQLite 存储历史推荐

## 2. 非目标

- ❌ 不做 GitHub OAuth Web 登录（用 PAT）
- ❌ 不做实时通知（走周期扫描 + 推送）
- ❌ 不替代 GitHub Trending 网页（只是过滤+定制）
- ❌ 不做项目管理（fork / clone / 通知合并）
- ❌ 不做团队共享（阶段一是单机单用户）
- ❌ 不做付费 API 调用（只用 GitHub 公共 API + LLM 可选）

## 3. 技术选型

| 层 | 选型 | 理由 |
|---|---|---|
| 语言 | Python 3.12 | 见 `agent-loop-scaffold` 锁定；LLM/数据分析生态最齐 |
| 包管理 | uv + .venv | 见脚手架 |
| CLI | Typer + Rich | 简单 + 自动生成 help |
| GitHub API | `httpx` + `PyGithub` | 后者做粗活，前者做流式抓 trending |
| 数据库 | SQLite（单文件） | 阶段一单机，无需 PostgreSQL |
| 关键字提取 | TF-IDF（sklearn）作 baseline + LLM 作可选升级 | TF-IDF 不需 API key，LLM 走 OpenAI/Anthropic |
| Trending 数据 | `gh-trending` PyPI 包 + search API 兜底 | trending 页面 HTML 解析 |
| 推送 | local / 飞书 webhook / SMTP | 三选一，配置文件切换 |
| 配置 | Pydantic Settings + .env | 类型安全 + 自动校验 |
| 测试 | pytest + pytest-cov + respx（mock httpx） | 见脚手架 §2 |
| 日志 | loguru | 简洁可读 |
| 周期任务 | 内置 daemon（asyncio） | 阶段一不引入 celery，外层用 launchd / crontab |

## 4. 架构图

```
┌─────────────────────────────────────────────────┐
│                   CLI (Typer)                    │
│   init   scan   daemon   keyword add/del/list   │
└──────┬──────────────┬───────────────────────────┘
       │              │
       ▼              ▼
┌─────────────┐  ┌────────────────┐
│  GitHub     │  │  Trending      │
│  Client     │  │  Client        │
│  (PyGithub) │  │  (httpx+HTML)  │
└──────┬──────┘  └────────┬───────┘
       │                  │
       ▼                  ▼
┌─────────────────────────────────────┐
│       Recommender Pipeline           │
│  stars ─→ keywords ─→ match ─→ rank │
└──────┬──────────────────────┬───────┘
       │                      │
       ▼                      ▼
┌─────────────┐  ┌──────────────────┐
│  SQLite     │  │  Push Targets    │
│  (history)  │  │  local/feishu/   │
│             │  │  email           │
└─────────────┘  └──────────────────┘
```

数据流：
1. **init**：GitHub API 拉 stars → SQLite 存 → 提取关键字（TF-IDF）→ SQLite 存
2. **scan**：Trending HTML / Search API 拉当日 → 关键字匹配打分 → 排序 → 推送 + 写历史
3. **daemon**：定时跑 scan，间隔由 .env 配置

## 5. 模块与边界

| 模块 | 责任 | 不允许做的事 |
|---|---|---|
| `ai_github_radar/cli/` | CLI 入口、参数解析 | 业务逻辑 |
| `ai_github_radar/github/` | GitHub API 客户端、Trending 解析 | 关键字匹配、推送 |
| `ai_github_radar/keywords/` | TF-IDF 提取、关键字 CRUD | GitHub 调用 |
| `ai_github_radar/recommender/` | 匹配算法、排序、打分 | 拉数据、推送 |
| `ai_github_radar/push/` | local / 飞书 / 邮件推送 | 拉数据 |
| `ai_github_radar/db/` | SQLite ORM、迁移 | 业务逻辑 |
| `ai_github_radar/config.py` | 配置加载、校验 | 业务实现 |

## 6. 数据 / 表

| 表 | 用途 | 关键字段 |
|---|---|---|
| `stars` | 已 star 仓库快照 | repo_id, owner, name, description, lang, topics, starred_at, fetched_at |
| `keywords` | 关键字订阅 | id, term, weight, source (auto/manual), enabled, created_at |
| `trending_snapshots` | trending 历史 | repo_id, snapshot_date, rank, stars_today, lang |
| `recommendations` | 已推送的推荐 | id, repo_id, score, matched_keywords, pushed_at, channel |

## 7. 关键 API（阶段一：CLI 子命令）

| 命令 | 用途 | 关键参数 |
|---|---|---|
| `init` | 拉 star + 提关键字 | `--user <name>`, `--no-llm` |
| `scan` | 单次扫描 + 推送 | `--limit 20`, `--push local` |
| `daemon` | 周期守护 | `--interval daily`, `--dry-run` |
| `keyword list/add/del` | 关键字管理 | `--term`, `--weight` |
| `report` | 历史推荐回顾 | `--since 30d` |

无 HTTP API（阶段一是 CLI 工具，不暴露服务端点）。

## 8. 服务进程管理

- daemon：`python -m ai_github_radar.cli daemon`（前台运行，asyncio 循环）
- 外部调度：macOS launchd（`~/Library/LaunchAgents/com.kevin.ai-github-radar.plist`）
- 不用 systemd / Docker / Kubernetes（阶段一单机）

## 9. 验收（阶段一）

完成判据：

- [ ] `uv run pytest -v` 全绿（≥ 80% 覆盖率）
- [ ] `uv run python scripts/audit-loop.py --strict` 通过
- [ ] A1-A13 设计文档全部填实（本文件 + docs/*）
- [ ] README 的"当前已实现功能"全部勾选
- [ ] 能跑通完整闭环：`init` → `scan` → 收到推送
- [ ] tag: `v0.1.0`（在 `CHANGELOG.md` 写 release notes）