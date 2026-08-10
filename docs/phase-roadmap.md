# A6 阶段路线 — ai-github-radar

> 阶段切换通过本文件跟踪。每个阶段结束跑 `audit-loop.py --strict` + 全量回归。

## 阶段一（v0.1.0 — 当前）：本地单机

**范围**：
- ✅ CLI：init / scan / daemon / keyword list|add|del|toggle / history / config
- ✅ 数据源：GitHub `/user/starred` + Trending HTML + Search API
- ✅ 关键字：TF-IDF baseline + LLM 可选升级
- ✅ 推送：local / feishu webhook / SMTP
- ✅ 存储：SQLite 单文件
- ✅ 测试：≥ 80% 覆盖率

**不在范围**：
- ❌ HTTP API
- ❌ 多用户 / 多账户
- ❌ Web UI
- ❌ 团队共享
- ❌ 跨平台 Windows GUI

**完成判据**（SPEC §9）：
- [x] README / SPEC / INSTALL 写完
- [ ] `tests/` 全绿
- [ ] `audit-loop.py --strict` 通过
- [ ] docs/* 8 必填全部完成
- [ ] `init` + `scan` 跑通闭环
- [ ] tag `v0.1.0` + CHANGELOG

**预计工期**：1-2 周（业余时间）

---

## 阶段二（v0.5.0）：守护 + 增强匹配

**新增**：
- macOS launchd plist 模板（自启动）
- 多账号支持（`.env` 配多个 RADAR_USER）
- LLM 升级路径稳定化（缓存摘要，避免每次重算）
- 关键字去重 / 合并（近义词聚类）
- 推送模板可定制（Markdown / JSON / HTML）
- 历史推荐的"已读 / 隐藏"标记

**存储变化**：
- 仍 SQLite，加 `users` / `recommendation_actions` 表
- 加 `keyword_clusters` 表（自动聚类）

**完成判据**：
- launchd 自启动测试通过
- 至少 3 个真实用户的 star 数据验证 TF-IDF 质量
- 飞书推送 + 邮件推送两条链路真实验证

---

## 阶段三（v1.0.0）：公开化 + 可选 MCP

**新增**：
- GitHub Releases 自动发布（CI）
- 可选 MCP server（让其他 AI agent 调 radar）
- README 加 badges / screenshot
- contribution guide

**存储变化**：
- 仍 SQLite（单机）
- 或可选切到 PostgreSQL（Docker compose）

**完成判据**：
- v1.0.0 在 PyPI / GitHub Release 发布
- README 加 usage gif / demo
- 至少 1 个外部贡献者 PR

---

## 阶段四（v1.5.0，未来考虑）

**可能方向**：
- Web UI（推荐列表 + 关键字编辑）
- 多用户账号体系
- 飞书 / 钉钉 / Slack 全 SDK 集成
- 与 Notion / Obsidian 双向同步（推荐入库到笔记）

**不承诺**：每个阶段都做，视情况调整。