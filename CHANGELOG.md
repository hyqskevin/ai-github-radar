# Changelog

All notable changes to ai-github-radar will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Frontend（Nuxt 4 + Nuxt UI + DESIGN.md）**
  - `app/web/` Nuxt 4 骨架（含 layouts/default.vue + 1 个 health 端点 + 占位首页）
  - DESIGN.md：基于 [google-labs-code/design.md](https://github.com/google-labs-code/design.md) 规范的 design token
  - `scripts/dev.sh` 统一启动脚本（后端 + 前端）
  - `package.json` 装 @nuxt/ui / pinia / @pinia/nuxt / tailwindcss v4
  - `app.config.ts` 把 DESIGN.md token 注入 Nuxt UI theme
- **后端 + 文档**
  - SPEC.md §3 加 frontend 栈选型
  - SPEC.md §4 架构图加 Nuxt SSR 层
  - SPEC.md §5 加 app/web 模块边界
  - SPEC.md §7.2 加 HTTP 端点（Nuxt Nitro server/api/）
  - SPEC.md §9 加 vitest + DESIGN.md lint 验收
  - docs/architecture.md 加 ADR 006（Nuxt 4 SSR + 127.0.0.1 单机）
  - docs/ui-design.md 新增（A4 必填）
  - docs/TODO.md 加 12 条 frontend TODO（T101-T112）

## [0.1.0] - TBD

### Added
- CLI：init / scan / daemon / keyword / history / config
- GitHub API 客户端（PyGithub 封装）
- Trending 抓取（HTML + search API fallback）
- TF-IDF 关键字提取
- LLM 关键字升级（OpenAI / Anthropic 可选）
- 推荐 pipeline（stars → keywords → match → rank）
- 推送：local Markdown / 飞书 webhook / SMTP
- SQLite 存储（4 张表）
- macOS launchd + Linux systemd 周期任务模板

### Documentation
- 13 维度设计文档（8 必填）
- 19 条 TODO（v0.1.0）
- INSTALL 跨平台指南