# TODO — ai-github-radar

> 走 [AGENTS.md §0 8 步 loop](../AGENTS.md) 的所有 TODO 都在这里跟踪。
> 每条 TODO 一行，状态用 `[ ]` / `[x]`。

## 阶段一（v0.1.0）

### 基础设施

- [x] **T001** — 项目骨架：建 src 目录、pyproject.toml 填依赖
  - spec：docs/superpowers/specs/2026-08-18-skeleton-design.md
  - AC：`uv run python -c "import ai_github_radar"` 成功 → ✅ 5/5 绿
  - src:`__init__.py`
- [x] **T002** — config.py：Pydantic Settings + .env 校验
  - spec：docs/superpowers/specs/2026-08-18-config-design.md
  - AC：`python -m ai_github_radar.config --validate` 退出码 0 → ✅ 10/10 绿
  - src:`config.py`
- [x] **T003** — db/models.py + db/session.py：SQLAlchemy 4 张表
  - spec：docs/superpowers/specs/2026-08-18-db-design.md
  - AC：`Base.metadata.create_all()` 成功，4 张表存在 → ✅ 15/15 绿
  - src:`db/__init__.py`、`db/models.py`、`db/session.py`
- [x] **T004** — github/client.py：PyGithub 封装 + stars 拉取
  - spec：docs/superpowers/specs/2026-08-18-github-client-design.md
  - AC：fetch_stars 返回 list[dict] 覆盖 12 字段,12/12 测试绿
  - src:`github/__init__.py`、`github/client.py`
- [x] **T005** — github/trending.py：HTML 解析 + search API(双路径:passive + active keyword)
  - spec：docs/superpowers/specs/2026-08-18-trending-design.md
  - AC：fetch_trending_html 解析 ≥ 20 条 + search_repositories 按关键词 + star 阈值筛选 → ✅ 16/16 绿
  - src:`github/trending.py`
  - 用户扩展：search API 支持 keywords 列表 + min_stars 阈值 + language 过滤 + per_page + sort/order

### 业务核心

- [x] **T006** — keywords/extractor.py + repository.py：TF-IDF 提取 + 关键字 CRUD
  - spec：docs/superpowers/specs/2026-08-18-keywords-design.md
  - AC：50 star → TF-IDF → repository → ≥ 30 keywords → ✅ 20/20 绿
  - src:`keywords/__init__.py`、`keywords/extractor.py`、`keywords/repository.py`
- [x] **T007** — keywords/llm_upgrade.py：多 LLM provider (OpenAI/Anthropic + 国产 DeepSeek/Qwen/Moonshot/Zhipu)
  - spec：docs/superpowers/specs/2026-08-18-llm-kw-design.md
  - AC：6 provider 注册 + openai 兼容协议分支 + anthropic 分支 + prompt + 重试 + 探测 → ✅ 19/19 绿
  - src:`keywords/llm_upgrade.py`,config 加 5 个新字段(llm_provider/llm_model/deepseek/dashscope/moonshot/zhipuai)
- [x] **T008** — recommender/pipeline.py：stars → keywords → match → rank
  - spec：docs/superpowers/specs/2026-08-18-recommender-design.md
  - AC：50 star → TF-IDF + user_keywords → 25 trending → ranked recs → ✅ 19/19 绿
  - src:`recommender/__init__.py`、`recommender/pipeline.py`
  - 关键设计:language token 屏蔽(避免 language 字段污染打分)、score = log(stars_today+2) + explicit_hit*5.0 + implicit_hit*weight
  - AC：scan 输出按 score 降序
- [x] **T009** — push/local.py：jinja2 Markdown + JSON + stdout 管道
  - spec：docs/superpowers/specs/2026-08-19-push-local-design.md
  - AC：默认 ./data/recommendations/YYYY-MM-DD.md + 自定义路径 + stdout 输出 → ✅ 22/22 绿
  - src:`push/__init__.py`、`push/local.py`
  - spec：docs/superpowers/specs/2026-08-10-push-local-design.md
  - AC：`scan --push local` 写到 `./data/recommendations/YYYY-MM-DD.md`
- [x] **T010** — push/feishu.py：飞书 webhook (interactive + text + HMAC-SHA256 签名)
  - spec：docs/superpowers/specs/2026-08-19-push-feishu-design.md
  - AC：interactive/text payload + 200/StatusCode==0 + 非 2xx 抛错 + 签名开关 + HMAC 基线 → ✅ 15/15 绿
  - src:`push/feishu.py`
  - spec：docs/superpowers/specs/2026-08-10-push-feishu-design.md
  - AC：飞书群收到消息（用真 webhook 测）
- [x] **T011** — push/email.py：SMTP multipart/alternative (HTML + text)
  - spec：docs/superpowers/specs/2026-08-19-push-email-design.md
  - AC：HTML 内联 CSS + text fallback + multipart + login/TLS 开关 + SMTP 异常 → ✅ 18/18 绿
  - src:`push/email.py`

### CLI + 周期

- [x] **T014** — storage/：db.py (session_scope) + repositories.py (Star/Trending/Recommendation)
  - spec：docs/superpowers/specs/2026-08-19-cli-design.md(被 T012 依赖,提前写)
  - AC：upsert / list_by_date / N-day dedupe → ✅ 6/6 绿
  - src:`storage/__init__.py`、`storage/db.py`、`storage/repositories.py`
- [x] **T011** — push/email.py：SMTP multipart/alternative (HTML + text)
  - spec：docs/superpowers/specs/2026-08-19-push-email-design.md
  - AC：HTML 内联 CSS + text fallback + multipart + login/TLS 开关 + SMTP 异常 → ✅ 18/18 绿
  - src:`push/email.py`

### CLI + 周期

- [x] **T012** — cli/(init/scan/keyword/web) — click 编排入口
  - spec：docs/superpowers/specs/2026-08-19-cli-design.md
  - AC：每个子命令 --help + exit code 0 + repo CRUD 走通 → ✅ 9/9 绿
  - src:`cli/__init__.py`、`cli/__main__.py`、`cli/init_cmd.py`、`cli/scan_cmd.py`、`cli/keyword_cmd.py`、`cli/web_cmd.py`
  - 入口:`python -m ai_github_radar.cli {init|scan|keyword|web}`
- [x] **T013** — web/ (FastAPI 本地 UI)
  - spec：docs/superpowers/specs/2026-08-19-web-design.md
  - AC：/ 渲染推荐 + /keywords 渲染表 + /api/keywords CRUD + /api/scan 触发 → ✅ 13/13 绿
  - src:`web/__init__.py`、`web/app.py`
  - 入口:`radar web` (uvicorn 阻塞) 或 TestClient 测
- [ ] **T014** — scripts/com.kevin.ai-github-radar.plist（macOS launchd）
  - spec：docs/scheduled-jobs.md
  - AC：launchctl load 不报错
- [x] **T015** — jobs/scheduler.py：in-process 周期调度 (run_once / run_forever)
  - spec：docs/superpowers/specs/2026-08-19-scheduler-design.md
  - AC：run_once 透传 + run_forever stop_event + 异常吞 + 参数透传 → ✅ 8/8 绿
  - src:`jobs/__init__.py`、`jobs/scheduler.py`
  - 复用 cli/scan_cmd.do_scan(扫描核心逻辑提到独立函数)

### 收尾

- [x] **T016** — 全量 audit + 覆盖率 ≥ 80% → ✅ 89% (237 tests, 0 ERROR / 0 WARN)
  - 顺手补 2 处真 bug:
    · config.get_settings alias (cli 之前引用不存在的函数)
    · 测试间 cache_clear(load_settings + DB engine)
- [x] **T017** — README 更新(5 步走 + 15/15 阶段一勾完 + 推送格式样例)
- [x] **T018** — CHANGELOG v0.1.0 release notes(Keep a Changelog 格式 + Fixed + Documentation)
- [x] **T019** — git tag v0.1.0 (`git tag -a v0.1.0 -m "..."`)

### Frontend（Nuxt 4 + Nuxt UI + DESIGN.md）

- [x] **T101-T110** — Nuxt 4 骨架 + 6 pages + Nitro API + DESIGN theme → ✅ 66/66 测试, 6 pages HTTP 200
  - 入口:`cd app/web && pnpm dev` → http://127.0.0.1:5173/
  - pages: / /keywords /recommendations /scan /stars /settings
  - API: /api/health /keywords(/[id]) /stars/stats /recommendations /scan
  - theme: DESIGN.md → app.config.ts + main.css @theme static 注入
- [ ] **T111** — DESIGN.md → `tailwind.theme.json` 导出脚本 + CI 集成
  - spec：docs/superpowers/specs/2026-08-10-design-export-design.md
  - AC：跑 `pnpm design:lint` 校验 + 导出
- [ ] **T112** — `scripts/dev.sh` 统一启动脚本（后端 + 前端）
  - spec：docs/superpowers/specs/2026-08-10-dev-script-design.md
  - AC：跑一次同时拉起 Python daemon + Nuxt dev

---

## 阶段二（v0.5.0）

- [ ] **T201** — LLM 摘要缓存
- [ ] **T202** — 多账号支持
- [ ] **T203** — 关键字近义词聚类
- [ ] **T204** — 推送模板可定制

## 阶段三（v1.0.0）

- [ ] **T301** — GitHub Release 自动发布 CI
- [ ] **T302** — MCP server
- [ ] **T303** — README badges / screenshot
- [ ] **T304** — PyPI 发布