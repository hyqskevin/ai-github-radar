# Changelog

All notable changes to ai-github-radar will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-19

阶段一收官版。15 个后端 TODO 全完成,237 单元测试,**89% 覆盖率**,`audit-loop --strict` 0 ERROR / 0 WARN。

### Added

#### CLI 编排(`python -m ai_github_radar.cli`)

- **`init`** — 拉 GitHub stars + 提关键字 + 入库(支持 `--no-llm` 强制 TF-IDF)
- **`scan`** — 拉 trending + 匹配 + 推送
  - `--push` 支持 `local` / `feishu` / `email` / `stdout` / `json`
  - `--top N` 限制推送条数
  - `--language` / `--since` 过滤 trending
  - `--min-score` 过滤低分
- **`keyword {list, add, del, toggle}`** — 关键字 CRUD 子命令组
- **`web`** — 启 FastAPI 本地 UI(默认 `127.0.0.1:8765`)

#### 后端核心模块

- **`db/`**(T001-T003) — 4 张表 ORM: stars / keywords / trending_snapshots / recommendations
- **`github/client.py`**(T004) — REST + GraphQL 拉 stars,指数退避处理 429
- **`github/trending.py`**(T005) — HTML 解析 + search API 双路径,支持语言/星级/排序
- **`keywords/extractor.py`**(T006) — sklearn TfidfVectorizer,默认 min_df=2 / ngram=(1,2)
- **`keywords/repository.py`**(T006) — KeywordRepository (CRUD + bulk_upsert)
- **`keywords/llm_upgrade.py`**(T007) — 6 个 LLM provider:
  - OpenAI / Anthropic
  - DeepSeek / Qwen (DashScope) / Moonshot (Kimi) / Zhipu (智谱 GLM)
  - 5/6 走 OpenAI 兼容协议(零成本扩展)
- **`recommender/pipeline.py`**(T008) — 匹配打分:
  - `score = log(stars_today+2) + explicit_hit*5.0 + implicit_hit*weight`
  - language token 屏蔽(避免 Python/Rust 字段污染)
  - 7-day dedupe + 跳过已 star
- **`storage/`**(T014) — session_scope + 3 个 Repository (Star / Trending / Recommendation)
- **`jobs/scheduler.py`**(T015) — in-process `run_once` + `run_forever`(threading.Event,可被 set() 唤醒)

#### 推送

- **`push/local.py`**(T009) — jinja2 Markdown + JSON,默认 `./data/recommendations/YYYY-MM-DD.{md,json}`,支持 stdout 管道
- **`push/feishu.py`**(T010) — 飞书自定义机器人,:
  - interactive card(标题 + 每条仓库段) / text(纯文本)
  - HMAC-SHA256 签名
  - 429/5xx 重试 1 次
- **`push/email.py`**(T011) — SMTP multipart/alternative (HTML + text fallback)
  - 内联 CSS,`html.escape` 防 XSS
  - `use_tls` / login 开关

#### Web UI(T013)

- `GET /` — 推荐列表 HTML
- `GET /keywords` — 关键字表 HTML(enabled 着色)
- `GET /api/keywords` / `POST` / `DELETE /{term}` / `POST /{term}/toggle` — JSON CRUD
- `GET /api/recommendations` — 最近 N 条推送
- `POST /api/scan` — 触发 scan(返回 recs)

#### 调度(T015)

- `run_once(*, push_target, top, language, since, min_score)` → int (recs 计数,失败返 -1)
- `run_forever(*, interval_seconds=86400, ..., stop_event)` — 阻塞跑,单次异常不退出 daemon

### Fixed

- `config.get_settings` alias (cli 之前引用不存在的函数,启动即崩)
- 测试间 cache reset: `load_settings.cache_clear()` + `storage.db.reset_for_testing()`

### Documentation

- `docs/superpowers/specs/2026-08-*.md` — 18 份 spec(每个 TODO 一份,TDD 前置)
- README 更新 — 「当前已实现功能」勾完 15 条

## [0.3.0] - 2026-08-19

集成层版本。前端 + 后端 + 设计系统端到端打通。

### Added

#### Nitro ↔ Python FastAPI 联调(T112)
- `app/web/server/utils/python.ts` — `pythonFetch<T>(path, opts, event)`
  - 读 `runtimeConfig.pythonBackendUrl` + 兼容 `PYTHON_BACKEND_URL` env
  - GET/POST/PATCH/DELETE + body + query + 2-5s timeout + AbortController
  - 返 `{ok, status, data, error}`
- `server/api/integration/health.get.ts` — 检测 Python 后端可达
  - 默认走 `runtimeConfig`
  - `?url=` 可 override(测试用)
- `server/api/keywords.get.ts` — 优先 pythonFetch,fallback mock store
- `tests/unit/python.test.ts` — 8 测试
  - default URL / env 覆盖 / 200 成功 / 500 / ECONNREFUSED / timeout / query / POST body

#### DESIGN token 一致性(T111)
- `scripts/design-check.py` — DESIGN.md ↔ main.css 交叉验证
  - 解析 YAML front-matter colors 块
  - 解析 `@theme static` 的 `--color-<name>-XXX` 声明
  - 校验 7 色双向同步
  - `--root <path>` + `--json`
- `scripts/audit-loop.py` 新增 `audit_l5()` 调 design-check.py
  - `KNOWN_LEVELS` 加 `L5`
- `app/web/app/assets/css/main.css` — 补 colors.primary 50-950 ramp
- `tests/unit/scripts/test_design_check.py` — 4 测试

#### Playwright e2e(T113)
- `playwright.config.ts` — chromium + baseURL + webServer 自启
- `tests/e2e/smoke.spec.ts` — 7 测试
  - Dashboard / Keywords / Scan / Settings 渲染
  - Sidebar 6 nav items
  - `/api/keywords` mock fallback
  - `/api/integration/health` reachable field

### Fixed

- `app/web/app/assets/css/main.css` — 补 primary token ramp(之前 edit 没保存)
- `scripts/design-check.py` — 正则 `\d{3}` → `\d{2,3}` + set comprehension fix

### Verified

- **前端**:`74 passed` unit + `7 passed` e2e
- **后端**:`241 passed` unit + 89% 覆盖率
- **audit-loop**:0 ERROR, 1 WARN (老的 TODO(017+018) commit prefix,无害)
- **design-check**:7/7 tokens 同步
- **端到端实测**:
  - `/api/integration/health` → `python_reachable: true, status: 200`
  - Nitro `/api/keywords` 透传 Python SQLite 数据
  - Python POST 加关键字 → Nitro 立刻看到

## [0.2.0] - 2026-08-19

前端版本。Nuxt 4 + Nitro + DESIGN theme + 6 pages。

### Added

- Nuxt 4 骨架 + 依赖(50+ package)
- `app.config.ts` + `main.css` @theme static 注入 7 色
- `layouts/default.vue` — AppBar + UNavigationMenu + Content
- 6 pages: index / keywords / recommendations / scan / stars / settings
- Nitro API: `/api/{health, keywords(/[id]), stars/stats, recommendations, scan}`
- 74 unit tests(vitest)

## [0.1.0] - 2026-08-19

阶段一收官版。15 个后端 TODO 全完成,237 单元测试,**89% 覆盖率**,`audit-loop --strict` 0 ERROR / 0 WARN。

### Added

#### CLI 编排(`python -m ai_github_radar.cli`)

- **`init`** — 拉 GitHub stars + 提关键字 + 入库(支持 `--no-llm` 强制 TF-IDF)
- **`scan`** — 拉 trending + 匹配 + 推送
  - `--push` 支持 `local` / `feishu` / `email` / `stdout` / `json`
  - `--top N` 限制推送条数
  - `--language` / `--since` 过滤 trending
  - `--min-score` 过滤低分
- **`keyword {list, add, del, toggle}`** — 关键字 CRUD 子命令组
- **`web`** — 启 FastAPI 本地 UI(默认 `127.0.0.1:8765`)

#### 后端核心模块

- **`db/`**(T001-T003) — 4 张表 ORM: stars / keywords / trending_snapshots / recommendations
- **`github/client.py`**(T004) — REST + GraphQL 拉 stars,指数退避处理 429
- **`github/trending.py`**(T005) — HTML 解析 + search API 双路径,支持语言/星级/排序
- **`keywords/extractor.py`**(T006) — sklearn TfidfVectorizer,默认 min_df=2 / ngram=(1,2)
- **`keywords/repository.py`**(T006) — KeywordRepository (CRUD + bulk_upsert)
- **`keywords/llm_upgrade.py`**(T007) — 6 个 LLM provider:
  - OpenAI / Anthropic
  - DeepSeek / Qwen (DashScope) / Moonshot (Kimi) / Zhipu (智谱 GLM)
  - 5/6 走 OpenAI 兼容协议(零成本扩展)
- **`recommender/pipeline.py`**(T008) — 匹配打分:
  - `score = log(stars_today+2) + explicit_hit*5.0 + implicit_hit*weight`
  - language token 屏蔽(避免 Python/Rust 字段污染)
  - 7-day dedupe + 跳过已 star
- **`storage/`**(T014) — session_scope + 3 个 Repository (Star / Trending / Recommendation)
- **`jobs/scheduler.py`**(T015) — in-process `run_once` + `run_forever`(threading.Event,可被 set() 唤醒)

#### 推送

- **`push/local.py`**(T009) — jinja2 Markdown + JSON,默认 `./data/recommendations/YYYY-MM-DD.{md,json}`,支持 stdout 管道
- **`push/feishu.py`**(T010) — 飞书自定义机器人,:
  - interactive card(标题 + 每条仓库段) / text(纯文本)
  - HMAC-SHA256 签名
  - 429/5xx 重试 1 次
- **`push/email.py`**(T011) — SMTP multipart/alternative (HTML + text fallback)
  - 内联 CSS,`html.escape` 防 XSS
  - `use_tls` / login 开关

#### Web UI(T013)

- `GET /` — 推荐列表 HTML
- `GET /keywords` — 关键字表 HTML(enabled 着色)
- `GET /api/keywords` / `POST` / `DELETE /{term}` / `POST /{term}/toggle` — JSON CRUD
- `GET /api/recommendations` — 最近 N 条推送
- `POST /api/scan` — 触发 scan(返回 recs)

#### 调度(T015)

- `run_once(*, push_target, top, language, since, min_score)` → int (recs 计数,失败返 -1)
- `run_forever(*, interval_seconds=86400, ..., stop_event)` — 阻塞跑,单次异常不退出 daemon

### Fixed

- `config.get_settings` alias (cli 之前引用不存在的函数,启动即崩)
- 测试间 cache reset: `load_settings.cache_clear()` + `storage.db.reset_for_testing()`

### Documentation

- `docs/superpowers/specs/2026-08-*.md` — 18 份 spec(每个 TODO 一份,TDD 前置)
- README 更新 — 「当前已实现功能」勾完 15 条

## [0.4.0] - 2026-08-19

本地部署 + 周期调度版本。macOS launchd / Linux systemd 双平台支持。

### Added

#### dev.sh 重写(T118)
- 同时拉起 Python 后端 `:8765` + Nuxt 前端 `:5173`
- 自动设 `PYTHON_BACKEND_URL=http://127.0.0.1:8765` 环境变量
- `wait_for_backend()` 等 `/api/keywords` 返 200 才启前端
- `trap SIGINT → kill 两端`
- 支持 `--backend` / `--frontend` / `BACKEND_PORT=9000`
- logs 写 `data/logs/{backend,frontend}.log`

#### macOS launchd(T116)
- `scripts/templates/com.ai-github-radar.scanner.plist`
  - `StartInterval=86400`(每 24h)
  - `RunAtLoad=true`(立刻)
  - `KeepAlive.SuccessfulExit/Crashed=false`(跑完即退出)
  - `PYTHONPATH=src` 注入 .venv
- `scripts/install-launchd.sh`
  - macOS-only (`uname -s == Darwin`)
  - 占位符替换 (`@PROJECT_ROOT@` `@PYTHON_BIN@` `@LOG_DIR@`)
  - `launchctl load` + 验证
  - `--dry-run` 支持
- `scripts/uninstall-launchd.sh` — `launchctl unload` + `rm plist`

#### Linux systemd user timer(T117)
- `scripts/templates/ai-github-radar-scan.service` — `Type=oneshot`
- `scripts/templates/ai-github-radar-scan.timer`
  - `OnBootSec=1min` + `OnUnitActiveSec=24h`
  - `Persistent=true`(错过调度时间会补跑)
- `scripts/install-systemd.sh`
  - Linux-only
  - `systemctl --user enable --now ai-github-radar-scan.timer`
  - 提示 `loginctl enable-linger`
- `scripts/uninstall-systemd.sh`

#### 测试(T115)
- `tests/unit/scripts/test_local_deploy.py` — 17 测试
  - plist 模板占位符 / sed 后合法 XML / `StartInterval=86400` / `KeepAlive=false`
  - systemd 模板 24h + Persistent + INI 合法
  - install/uninstall 脚本可执行
  - `--dry-run` 不破坏系统(macOS/Linux cross-platform skip)

### Verified

- `./scripts/dev.sh` → 18s 后两端 HTTP 200
- `/api/integration/health` → `python_reachable: true`
- `./scripts/install-launchd.sh --dry-run` → `[DRY-RUN]` 输出,无副作用
- `./scripts/install-systemd.sh` (macOS) → 友好 refuse "use install-launchd.sh on macOS"
- 后端:`256 passed` unit (含 17 local_deploy)
- audit:`0 ERROR,1 WARN`(老的 commit prefix)

## [Unreleased]

阶段二规划:

- LLM 摘要缓存(同 stars 输入复用)
- 多用户隔离
- WebSocket 实时推送
- 嵌入相似度(替代 TF-IDF 关键字精确匹配)
- CI(github actions 跑 tests + audit + e2e)

[0.4.0]: #040----2026-08-19
[0.3.0]: #030----2026-08-19
[0.2.0]: #020----2026-08-19
[0.1.0]: #010----2026-08-19