# ai-github-radar

> **AI 驱动的 GitHub 项目发现工具** — 从你的 star 历史建模偏好，提取关键字，定期扫描 trending 给你推送匹配的项目。

## 它解决什么问题

用 AI 写代码的人常陷入"不知道新出了什么好东西"的循环：

- ✗ 每周手动刷 GitHub Trending 浪费时间
- ✗ 看了 trending 但跟自己关注的方向不匹配
- ✗ 之前 star 过的项目已经烂掉了 / 找到更好的不知道
- ✗ 朋友推荐一个项目，要花半小时判断值不值得看

这个工具**自动化 4 件事**：

1. **拉你的 star** — GitHub API 拉所有 star 仓库 + 描述 + 主题 + 语言
2. **提取关键字** — 用 AI / TF-IDF 找出你 star 过的项目里高频技术信号
3. **维护关键字订阅** — 让你增删关键字（GUI / CLI 都行）
4. **周期抓 trending** — 每天 / 每周跑一次 GitHub Trending / search API，过滤出匹配关键字的新项目，推送到你常用的地方（飞书 / 邮件 / 本地文件）

## 怎么用 — 4 步走

### 第 1 步：克隆

```bash
git clone https://github.com/hyqskevin/ai-github-radar.git
cd ai-github-radar
```

### 第 2 步：装环境

```bash
# Python（uv + .venv，路径锁在项目内）
bash scripts/setup-python.sh

# Node（nvm + 项目内 node_modules）
bash scripts/setup-node.sh
```

### 第 3 步：配置

```bash
# 复制模板
cp config/.env.example .env

# 编辑 .env，填：
#   GITHUB_TOKEN=<Personal Access Token, scope: public_repo>
#   RADAR_USER=<你的 GitHub username>
#   RADAR_FETCH_INTERVAL=daily          # daily | weekly
#   RADAR_PUSH_TARGET=local              # local | feishu | email
```

### 第 4 步：跑

```bash
# 一次性：拉你的 star + 提取关键字
python -m ai_github_radar.cli init

# 一次性：抓 trending + 匹配 + 输出推荐
python -m ai_github_radar.cli scan

# 周期任务（crontab / launchd）
python -m ai_github_radar.cli daemon
```

## 当前已实现功能

> 按 [SPEC.md §9 验收清单](./SPEC.md) 跟踪。当前阶段一：
>
> - [ ] GitHub star 拉取
> - [ ] 关键字提取（LLM / TF-IDF）
> - [ ] 关键字订阅管理
> - [ ] GitHub Trending 抓取
> - [ ] 关键字匹配 + 推荐排序
> - [ ] 推送（local / 飞书 / 邮件）
> - [ ] 周期守护进程

## 设计文档（13 维度）

按 `agent-loop-scaffold` 标准，必填 7 份 + 提示型 3 份：

- [SPEC.md](./SPEC.md) — A1 总设计
- [docs/api-doc.md](./docs/api-doc.md) — A2 接口设计
- [docs/database-design.md](./docs/database-design.md) — A3 数据库设计
- [docs/architecture.md](./docs/architecture.md) — A5 架构决策
- [docs/phase-roadmap.md](./docs/phase-roadmap.md) — A6 阶段路线
- [docs/observability.md](./docs/observability.md) — A8 可观测性
- [docs/scheduled-jobs.md](./docs/scheduled-jobs.md) — A13 定时任务

## 开发规范

走 8 步 loop（见 [AGENTS.md §0](./AGENTS.md)）：

```
[1] 文档前置  [2] TODO 提出  [3] spec 设计  [4] TDD 红
[5] 实现→绿  [6] 重构       [7] audit     [8] commit
```

自查：

```bash
python3 scripts/audit-loop.py --strict
```

## License

MIT