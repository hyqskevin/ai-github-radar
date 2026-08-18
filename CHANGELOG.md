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

## [Unreleased]

阶段二规划:

- macOS launchd / Linux systemd 周期调度脚本
- LLM 摘要缓存(同 stars 输入复用)
- Docker 镜像
- 多用户隔离
- WebSocket 实时推送
- 嵌入相似度(替代 TF-IDF 关键字精确匹配)

[0.1.0]: #010----2026-08-19