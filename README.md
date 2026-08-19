# ai-github-radar

> **AI 驱动的 GitHub 项目发现工具** — 从你的 star 历史建模偏好，提取关键字，定期扫描 trending 给你推送匹配的项目。

[![backend-ci](https://github.com/hyqskevin/ai-github-radar/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/hyqskevin/ai-github-radar/actions/workflows/backend-ci.yml)
[![frontend-ci](https://github.com/hyqskevin/ai-github-radar/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/hyqskevin/ai-github-radar/actions/workflows/frontend-ci.yml)
[![ci](https://github.com/hyqskevin/ai-github-radar/actions/workflows/ci.yml/badge.svg)](https://github.com/hyqskevin/ai-github-radar/actions/workflows/ci.yml)

## 它解决什么问题

用 AI 写代码的人常陷入"不知道新出了什么好东西"的循环：

- ✗ 每周手动刷 GitHub Trending 浪费时间
- ✗ 看了 trending 但跟自己关注的方向不匹配
- ✗ 之前 star 过的项目已经烂掉了 / 找到更好的不知道
- ✗ 朋友推荐一个项目，要花半小时判断值不值得看

这个工具**自动化 4 件事**：

1. **拉你的 star** — GitHub API 拉所有 star 仓库 + 描述 + 主题 + 语言
2. **提取关键字** — 用 TF-IDF 或 LLM 找出你 star 过的项目里高频技术信号
3. **维护关键字订阅** — 本地 CLI / Web UI 增删关键字
4. **周期抓 trending** — 每天 / 每周跑一次 GitHub Trending / search API，过滤出匹配关键字的新项目，推送到你常用的地方（飞书 / 邮件 / 本地文件 / Web dashboard）

## 怎么用 — 5 步走

### 第 1 步：克隆

```bash
git clone https://github.com/hyqskevin/ai-github-radar.git
cd ai-github-radar
```

### 第 2 步：装环境

```bash
# Python 3.12 + .venv(路径锁在项目内)
bash scripts/setup-python.sh
```

### 第 3 步：配置

```bash
# 复制模板
cp config/.env.example .env

# 编辑 .env,填:
#   GITHUB_TOKEN=<Personal Access Token, scope: public_repo>
#   RADAR_USER=<你的 GitHub username>
# 可选:
#   OPENAI_API_KEY / ANTHROPIC_API_KEY / DEEPSEEK_API_KEY / DASHSCOPE_API_KEY
#   / MOONSHOT_API_KEY / ZHIPUAI_API_KEY (用 LLM 提关键字)
#   FEISHU_WEBHOOK_URL (飞书推送)
#   SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD / SMTP_TO (邮件推送)
```

### 第 4 步：跑

```bash
# 选项 A:一次性完整闭环
uv run python -m ai_github_radar.cli init   # 拉 star + 提关键字
uv run python -m ai_github_radar.cli scan   # 扫描 + 推送

# 选项 B:起 Web UI (默认 127.0.0.1:8765)
uv run python -m ai_github_radar.cli web

# 选项 C:周期守护(默认 24h 一次)
uv run python -m ai_github_radar.cli web    # Web UI(同时启用)
# 后台进程: python -c "from ai_github_radar.jobs import run_forever; run_forever()"
```

### 第 5 步:关键字管理

```bash
uv run python -m ai_github_radar.cli keyword list
uv run python -m ai_github_radar.cli keyword add fastapi --weight 5.0
uv run python -m ai_github_radar.cli keyword toggle agent
uv run python -m ai_github_radar.cli keyword del python
```

## 周期调度(后台跑)

不用 cron,直接用 OS 自带的调度器:

```bash
# macOS (launchd)
./scripts/install-launchd.sh
# 验证: launchctl list | grep ai-github-radar
# 日志: data/logs/scanner.log
# 卸载: ./scripts/uninstall-launchd.sh

# Linux (systemd user timer)
./scripts/install-systemd.sh
# 验证: systemctl --user list-timers | grep ai-github-radar
# 日志: data/logs/scanner.log
# 卸载: ./scripts/uninstall-systemd.sh
```

**调度行为**:每 24h 自动跑 `python -m ai_github_radar scan --push local --top 10`,结果写 `./data/recommendations/YYYY-MM-DD.md`。

`RunAtLoad=true` / `OnBootSec=1min` → 装上立刻跑一次。

不需要 root:launchd 用 `~/Library/LaunchAgents/`,systemd 用 `~/.config/systemd/user/`(建议 `sudo loginctl enable-linger $USER` 让 timer 在 logout 后继续)。

## 当前已实现功能

### 阶段一 ✅ 后端 + 前端 + 部署 + CI

#### 后端(v0.1.0)
- [x] **项目骨架** — Python 3.12 + .venv + pyproject + 8 步 loop
- [x] **SPEC + 13 维度设计文档** — SPEC.md / DESIGN.md / 8 份 docs/
- [x] **DB 层**(T001-T003) — 4 张表(stars / keywords / trending_snapshots / recommendations),SQLAlchemy ORM + session 管理
- [x] **GitHub API client**(T004) — 拉 stars + REST + GraphQL + 429 退避
- [x] **Trending 抓取**(T005) — HTML 解析 + search API 双路径(语言/星级/排序可配)
- [x] **关键字提取**(T006-T007) — TF-IDF baseline + 多 LLM provider(OpenAI / Anthropic + 国产 DeepSeek / Qwen / Moonshot / Zhipu)
- [x] **匹配打分**(T008) — stars→keywords→match→rank,language 屏蔽 + 7-day dedupe
- [x] **本地推送**(T009) — jinja2 Markdown + JSON + stdout 管道,默认 `./data/recommendations/YYYY-MM-DD.{md,json}`
- [x] **飞书推送**(T010) — webhook + interactive card + text + HMAC-SHA256 签名
- [x] **邮件推送**(T011) — SMTP multipart/alternative (HTML + text),XSS 转义
- [x] **CLI 编排**(T012) — `init / scan / keyword / web` 子命令
- [x] **Web UI**(T013) — FastAPI 本地 UI,渲染推荐 / 关键字表 + REST API CRUD
- [x] **存储层**(T014) — `session_scope` + 3 个 Repository
- [x] **周期调度**(T015) — in-process `run_forever` + `run_once`,stop_event 优雅退出
- [x] **测试 + audit**(T016) — 276 单元测试,**89% 覆盖率**,`audit-loop --strict` 0 ERROR / 0 WARN

#### 前端(v0.2.0)
- [x] **Nuxt 4 骨架**(T101) — `pnpm dev` 起服务,HTTP 200
- [x] **DESIGN theme**(T102) — `app.config.ts` + `main.css` @theme static 注入 7 色
- [x] **Layout**(T103) — AppBar + SideNav (`UNavigationMenu` 6 items) + Content
- [x] **6 pages**(T106-T110) — Dashboard / Keywords / Recommendations / Scan / Stars / Settings
- [x] **Nitro API**(T105) — `/api/{health, keywords, stars, recommendations, scan}` (mock fallback)

#### 集成层(v0.3.0)
- [x] **Nitro ↔ Python 联调**(T112) — `server/utils/python.ts` + `/api/integration/health`,timeout 2s + mock fallback
- [x] **DESIGN ↔ main.css 交叉验证**(T111) — `scripts/design-check.py` + audit L5
- [x] **Playwright e2e**(T113) — 7 测试覆盖 6 pages + 2 API,真 Chromium 跑

#### 本地部署(v0.4.0)
- [x] **一键 dev.sh**(T118) — 同时拉起后端 :8765 + 前端 :5173,自动 `wait_for_backend` + trap kill
- [x] **macOS launchd**(T116) — `~/Library/LaunchAgents/` plist 每 24h 跑 `python -m ai_github_radar scan`
- [x] **Linux systemd timer**(T117) — `~/.config/systemd/user/` service + timer,Persistent=true 补跑
- [x] **install/uninstall 脚本**(T119) — 都支持 `--dry-run`,OS 守卫 + 友好提示

#### CI(v0.5.0)
- [x] **GitHub Actions backend-ci**(T122) — ruff + pytest --cov-fail-under=80 + audit-loop --strict + design-check + codecov
- [x] **GitHub Actions frontend-ci**(T123) — pnpm test + build + preview + Playwright e2e (chromium),failure 时 upload 报告
- [x] **总入口 ci.yml**(T122) — reusable workflow 并行 backend + frontend
- [x] **paths 过滤**(T121) — 避免前端 PR 误触发后端 CI

### 下一阶段(阶段二)
- [ ] LLM 摘要缓存(同 stars 输入复用)
- [ ] 多用户隔离
- [ ] 嵌入相似度(替代 TF-IDF 关键字精确匹配)

## 设计文档(13 维度)

按 `agent-loop-scaffold` 标准,必填 8 份:

- [SPEC.md](./SPEC.md) — A1 总设计(9 段)
- [DESIGN.md](./DESIGN.md) — design token(Google design.md 规范)
- [docs/api-doc.md](./docs/api-doc.md) — A2 接口设计(CLI + HTTP)
- [docs/database-design.md](./docs/database-design.md) — A3 数据库设计
- [docs/architecture.md](./docs/architecture.md) — A5 架构决策(6 条 ADR)
- [docs/phase-roadmap.md](./docs/phase-roadmap.md) — A6 阶段路线
- [docs/observability.md](./docs/observability.md) — A8 可观测性
- [docs/deployment.md](./docs/deployment.md) — A9 部署与运维
- [docs/scheduled-jobs.md](./docs/scheduled-jobs.md) — A13 定时任务

## 推送格式

### Markdown(默认)

```markdown
# GitHub Radar 推荐 — 2026-08-19

> 生成时间: 2026-08-19T12:00:00+00:00  |  候选: 5 条

## 1. 🐍 [owner1/repo1](https://github.com/owner1/repo1)
Python FastAPI async web framework

- **Score**: `12.340`
- **Stars today**: `200`
- **Matched keywords**: `fastapi`, `async`

---
```

### 飞书 Card

富文本卡片,每个仓库一段,含 emoji + 链接 + 元数据。

### 邮件

multipart/alternative(HTML + text fallback),内联 CSS,HTML 转义防 XSS。

## 开发规范

走 8 步 loop(见 [AGENTS.md §0](./AGENTS.md)):

```
[1] 文档前置  [2] TODO 提出  [3] spec 设计  [4] TDD 红
[5] 实现→绿  [6] 重构       [7] audit     [8] commit
```

自查:

```bash
# 后端
python3 scripts/audit-loop.py
PYTHONPATH=src .venv/bin/python -m pytest tests/unit --cov=ai_github_radar

# 前端 unit
cd app/web && pnpm test

# 前端 e2e (需要 dev server 跑着)
cd app/web && pnpm test:e2e

# DESIGN token 一致性(L5)
python3 scripts/design-check.py
```

### 端到端联调(同时跑两个服务)

```bash
# 终端 1: Python 后端
python -m ai_github_radar.cli web --port 8765

# 终端 2: Nuxt 前端 (指向真后端)
cd app/web && PYTHON_BACKEND_URL=http://127.0.0.1:8765 pnpm dev

# 验证联调
curl http://127.0.0.1:5173/api/integration/health
# {"python_reachable": true, "python_status": 200, ...}
```

## License

MIT

## 致谢

- [agent-loop-scaffold](https://github.com/hyqskevin/agent-loop-scaffold) — 8 步 loop 标准
- [Google design.md](https://github.com/google-labs-code/design.md) — design token 规范
- [sklearn](https://scikit-learn.org) — TF-IDF 基线
- [click](https://click.palletsprojects.com) — CLI 框架
- [FastAPI](https://fastapi.tiangolo.com) — Web UI