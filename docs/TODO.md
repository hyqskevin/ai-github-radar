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

- [ ] **T012** — cli/init.py + cli/scan.py + cli/keyword.py + cli/history.py
  - spec：docs/superpowers/specs/2026-08-10-cli-design.md
  - AC：每个子命令 `--help` 输出符合 `docs/api-doc.md`
- [ ] **T013** — cli/daemon.py：asyncio 周期守护
  - spec：docs/superpowers/specs/2026-08-10-daemon-design.md
  - AC：`daemon` 前台跑 30 秒能触发 1 次 scan
- [ ] **T014** — scripts/com.kevin.ai-github-radar.plist（macOS launchd）
  - spec：docs/scheduled-jobs.md
  - AC：launchctl load 不报错
- [ ] **T015** — scripts/ai-github-radar.{service,timer}（Linux systemd）
  - spec：docs/scheduled-jobs.md
  - AC：systemctl daemon-reload 不报错

### 收尾

- [ ] **T016** — 全量 audit + 覆盖率 ≥ 80%
- [ ] **T017** — README 勾完"当前已实现功能"
- [ ] **T018** — CHANGELOG.md 写 v0.1.0 release notes
- [ ] **T019** — git tag v0.1.0

### Frontend（Nuxt 4 + Nuxt UI + DESIGN.md）

- [ ] **T101** — `app/web/` Nuxi init + 装 nuxt / @nuxt/ui / pinia / @pinia/nuxt
  - spec：docs/superpowers/specs/2026-08-10-nuxi-init-design.md
  - AC：`pnpm dev` 起服务，`curl http://127.0.0.1:5173` 返回 200
- [ ] **T102** — `app/web/app.config.ts` 把 DESIGN.md 导出为 Nuxt UI theme
  - spec：docs/superpowers/specs/2026-08-10-theme-design.md
  - AC：色板跟 DESIGN.md 一致；`npx -y @google/design.md lint DESIGN.md` 0 ERROR
- [ ] **T103** — `app/web/layouts/default.vue` 全局布局（AppBar + SideNav + content）
  - spec：docs/superpowers/specs/2026-08-10-layout-design.md
  - AC：vitest snapshot 通过
- [ ] **T104** — Pinia stores（keywords / recommendations / stars / scan / settings）
  - spec：docs/superpowers/specs/2026-08-10-pinia-design.md
  - AC：每个 store 至少 3 个 action，覆盖成功 / 错误 / 加载态
- [ ] **T105** — `app/web/server/api/keywords.get.ts` + `keywords.post.ts` 等 9 个端点
  - spec：docs/superpowers/specs/2026-08-10-nitro-api-design.md
  - AC：每个端点用 curl 实测；vitest mock Python 函数
- [ ] **T106** — `pages/index.vue` Dashboard（推荐卡片网格）
  - spec：docs/superpowers/specs/2026-08-10-page-dashboard-design.md
  - AC：@nuxt/test-utils 渲染成功；playwright e2e 能点详情
- [ ] **T107** — `pages/keywords.vue` 关键字管理表格
  - spec：docs/superpowers/specs/2026-08-10-page-keywords-design.md
  - AC：表格增删改 + 启停全部 vitest 覆盖
- [ ] **T108** — `pages/recommendations.vue` + `[id].vue` 推荐列表 / 详情
  - spec：docs/superpowers/specs/2026-08-10-page-recs-design.md
- [ ] **T109** — `pages/scan.vue` 手动触发 + 历史
  - spec：docs/superpowers/specs/2026-08-10-page-scan-design.md
- [ ] **T110** — `pages/stars.vue` + `pages/settings.vue`
  - spec：docs/superpowers/specs/2026-08-10-page-stars-settings-design.md
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