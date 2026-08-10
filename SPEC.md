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
| 后端语言 | Python 3.12 | 见 `agent-loop-scaffold` 锁定；LLM/数据分析生态最齐 |
| 前端框架 | Nuxt 4 | SSR 全栈一体，CLI + Web dashboard 同进程，单人单机零运维 |
| 前端语言 | Vue 3 + TypeScript | Nuxt 4 原生 |
| 状态管理 | Pinia | Vue 官方，TS 原生支持好，Nuxt 4 生态对齐 |
| UI 组件库 | Nuxt UI | Nuxt 4 原生集成，几行代码出页面 |
| 设计规范 | [DESIGN.md](./DESIGN.md)（google-labs-code/design.md） | 单文件 design token，AI 工具能读懂，导出 Tailwind/DTCG |
| 前后端通信 | Nuxt server/api/（Nitro） | 跟 Nuxt 同进程，无需独立 FastAPI |
| 包管理 | uv + .venv（后端）/ pnpm（前端） | uv 见脚手架；pnpm 速度 + 磁盘节省 |
| CLI | Typer + Rich | 简单 + 自动生成 help |
| GitHub API | `httpx` + `PyGithub` | 后者做粗活，前者做流式抓 trending |
| 数据库 | SQLite（单文件） | 阶段一单机，无需 PostgreSQL |
| 关键字提取 | TF-IDF（sklearn）作 baseline + LLM 作可选升级 | TF-IDF 不需 API key，LLM 走 OpenAI/Anthropic |
| Trending 数据 | `gh-trending` PyPI 包 + search API 兜底 | trending 页面 HTML 解析 |
| 推送 | local / 飞书 webhook / SMTP | 三选一，配置文件切换 |
| 配置 | Pydantic Settings + .env | 类型安全 + 自动校验 |
| 测试（后端） | pytest + pytest-cov + respx（mock httpx） | 见脚手架 §2 |
| 测试（前端） | vitest（unit）+ @nuxt/test-utils（integration）+ playwright（e2e） | Nuxt 4 推荐 |
| 日志 | loguru | 简洁可读 |
| 周期任务 | 内置 daemon（asyncio）+ launchd | 阶段一不引入 celery |

## 4. 架构图

```
┌──────────────────────────────────────────────────────────────┐
│                    Nuxt 4 SSR 全栈一体                          │
│                       绑 127.0.0.1                              │
│  ┌────────────────────────┐    ┌────────────────────────────┐ │
│  │   Vue 3 + Pinia       │    │  Nuxt server/api/ (Nitro)  │ │
│  │   Nuxt UI components  │ <─>│  HTTP REST 端点            │ │
│  │   DESIGN.md tokens    │    │  ┌────────────────────────┐ │ │
│  │   (inter / IBM Plex)  │    │  │  Python CLI / 后端     │ │ │
│  └────────────────────────┘    │  │  (Typer + FastAPI 嵌入)│ │ │
│                                │  └───────────┬────────────┘ │ │
│                                └──────────────┼──────────────┘ │
└───────────────────────────────────────────────│───────────────┘
                                                │
        ┌───────────────────────────────────────┼─────────────────┐
        │                                       │                 │
        ▼                                       ▼                 ▼
┌───────────────┐  ┌─────────────────┐  ┌──────────────┐  ┌────────────┐
│  GitHub API   │  │  Trending       │  │   SQLite     │  │  Push      │
│  Client       │  │  Client         │  │   (history)  │  │  local/    │
│  (PyGithub)   │  │  (httpx+HTML)   │  │              │  │  feishu/   │
│               │  │                 │  │              │  │  email     │
└───────────────┘  └─────────────────┘  └──────────────┘  └────────────┘

数据流：
1. init:   GitHub API 拉 stars → 关键字提取（TF-IDF/LLM） → SQLite
2. scan:   Trending / Search API 拉当日 → 关键字匹配 → 排序 → 推送
3. web:    浏览器 → Nuxt SSR → Nitro server/api/ → 调 Python 函数
4. daemon: launchd 触发 scan 周期任务
```

## 5. 模块与边界

| 模块 | 责任 | 不允许做的事 |
|---|---|---|
| `src/ai_github_radar/cli/` | CLI 入口、参数解析 | 业务逻辑 |
| `src/ai_github_radar/github/` | GitHub API 客户端、Trending 解析 | 关键字匹配、推送 |
| `src/ai_github_radar/keywords/` | TF-IDF 提取、关键字 CRUD | GitHub 调用 |
| `src/ai_github_radar/recommender/` | 匹配算法、排序、打分 | 拉数据、推送 |
| `src/ai_github_radar/push/` | local / 飞书 / 邮件推送 | 拉数据 |
| `src/ai_github_radar/db/` | SQLite ORM、迁移 | 业务逻辑 |
| `src/ai_github_radar/config.py` | 配置加载、校验 | 业务实现 |
| `src/ai_github_radar/api/` | Nuxt Nitro 调用的 Python 函数（被 server/api/ 包装） | 直接接 HTTP |
| `app/web/` | Nuxt 4 前端（pages/ + components/ + server/api/） | 业务计算 |
| `app/web/server/api/` | Nitro HTTP 端点（薄壳，调 Python src/） | 写业务逻辑 |
| `app/web/pages/` | 页面路由 | 直接调 GitHub API |
| `app/web/components/` | Vue 组件 | 直接 fetch DB |
| `app/web/composables/` | 复用逻辑 | 写业务 |
| `app/web/stores/` | Pinia store | 直连后端（用 $fetch） |

## 6. 数据 / 表

| 表 | 用途 | 关键字段 |
|---|---|---|
| `stars` | 已 star 仓库快照 | repo_id, owner, name, description, lang, topics, starred_at, fetched_at |
| `keywords` | 关键字订阅 | id, term, weight, source (auto/manual), enabled, created_at |
| `trending_snapshots` | trending 历史 | repo_id, snapshot_date, rank, stars_today, lang |
| `recommendations` | 已推送的推荐 | id, repo_id, score, matched_keywords, pushed_at, channel |

## 7. 关键 API

### 7.1 CLI 子命令（Python Typer）

| 命令 | 用途 | 关键参数 |
|---|---|---|
| `init` | 拉 star + 提关键字 | `--user <name>`, `--no-llm` |
| `scan` | 单次扫描 + 推送 | `--limit 20`, `--push local` |
| `daemon` | 周期守护 | `--interval daily`, `--dry-run` |
| `keyword list/add/del` | 关键字管理 | `--term`, `--weight` |
| `report` | 历史推荐回顾 | `--since 30d` |

### 7.2 HTTP 端点（Nuxt Nitro server/api/）

绑 `127.0.0.1:5173/api/...`，仅本机访问。Nuxt 启动时一并启 Python 进程（或反向）。

| 方法 | 路径 | 鉴权 | 用途 |
|---|---|---|---|
| GET | `/api/recommendations` | 无（127.0.0.1） | 推荐列表（分页） |
| GET | `/api/recommendations/:id` | 无 | 单条详情 |
| GET | `/api/keywords` | 无 | 关键字列表 |
| POST | `/api/keywords` | 无 | 加关键字 |
| PATCH | `/api/keywords/:id` | 无 | 改权重 / 启停 |
| DELETE | `/api/keywords/:id` | 无 | 删关键字 |
| GET | `/api/stars/stats` | 无 | star 统计（语言 / 主题分布） |
| POST | `/api/scan` | 无 | 触发单次扫描（dry-run 选项） |
| GET | `/api/health` | 无 | 健康检查 |

完整列表见 `docs/api-doc.md`。

## 8. 服务进程管理

- **后端 CLI**：`python -m ai_github_radar.cli <subcmd>`（一次性任务）
- **后端 daemon**：`python -m ai_github_radar.cli daemon`（asyncio 周期）
- **前端 dev**：`cd app/web && pnpm dev`（Nuxt dev server，绑 127.0.0.1:5173）
- **前端 prod**：`cd app/web && pnpm build && pnpm start`
- **统一启动**：`./scripts/dev.sh`（后端 + 前端一起拉起，热重载）
- 改 ORM / migration -> 验收项必含"重启 daemon + 重启 Nuxt"

## 9. 验收（阶段一）

完成判据：

- [ ] `pnpm test`（前端 vitest）+ `uv run pytest -v`（后端）全绿，覆盖率 ≥ 80%
- [ ] `uv run python scripts/audit-loop.py --strict` 通过
- [ ] A1-A13 设计文档全部填实（本文件 + docs/*）
- [ ] DESIGN.md 通过 `npx -y @google/design.md lint` 校验，0 ERROR
- [ ] README 的"当前已实现功能"全部勾选
- [ ] 能跑通完整闭环：`init` → `scan` → Web UI 看到推荐 → 触发推送
- [ ] tag: `v0.1.0`（在 `CHANGELOG.md` 写 release notes）