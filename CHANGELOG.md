# Changelog

All notable changes to ai-github-radar will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 项目骨架：按 agent-loop-scaffold 标准搭 18 目录
- AGENTS.md / SPEC.md / INSTALL.md / README.md
- docs/：api-doc / database-design / architecture / phase-roadmap / observability / deployment / scheduled-jobs / TODO

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