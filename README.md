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
2. **提取关键字** — 用 TF-IDF 或 LLM 找出你 star 过的项目里高频技术信号
3. **维护关键字订阅** — Web dashboard（Nuxt 4 + Nuxt UI）或 CLI 增删关键字
4. **周期抓 trending** — 每天 / 每周跑一次 GitHub Trending / search API，过滤出匹配关键字的新项目，推送到你常用的地方（飞书 / 邮件 / 本地文件 / Web dashboard）

## 怎么用 — 5 步走

### 第 1 步：克隆

```bash
git clone https://github.com/hyqskevin/ai-github-radar.git
cd ai-github-radar
```

### 第 2 步：装环境

```bash
# Python（uv + .venv，路径锁在项目内）
bash scripts/setup-python.sh

# Node（pnpm，路径锁在项目内）
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
# 选项 A：统一启动（推荐，同时拉起后端 + 前端）
./scripts/dev.sh

# 选项 B：分开跑
# 终端 1：后端 daemon
uv run python -m ai_github_radar.cli daemon

# 终端 2：前端 dev server
cd app/web && pnpm dev
```

打开 http://127.0.0.1:5173 看 Web dashboard。

### 第 5 步：跑一次性命令

```bash
# 拉你的 star + 提取关键字
uv run python -m ai_github_radar.cli init

# 一次性扫描 trending
uv run python -m ai_github_radar.cli scan
```

## 当前已实现功能

> 按 [SPEC.md §9 验收清单](./SPEC.md) 跟踪。当前阶段一：

- [x] 项目骨架（Nuxt 4 + Python + DESIGN.md）
- [x] SPEC + 13 维度设计文档
- [x] DESIGN.md（Google design.md 规范）
- [x] `scripts/dev.sh` 统一启动脚本
- [ ] T101-T019 / T101-T112（详见 `docs/TODO.md`）

## 设计文档（13 维度）

按 `agent-loop-scaffold` 标准，必填 8 份：

- [SPEC.md](./SPEC.md) — A1 总设计（9 段）
- [DESIGN.md](./DESIGN.md) — design token（Google design.md 规范）
- [docs/api-doc.md](./docs/api-doc.md) — A2 接口设计（CLI + HTTP）
- [docs/database-design.md](./docs/database-design.md) — A3 数据库设计
- [docs/ui-design.md](./docs/ui-design.md) — A4 UI 设计（Nuxt 4 dashboard）
- [docs/architecture.md](./docs/architecture.md) — A5 架构决策（6 条 ADR）
- [docs/phase-roadmap.md](./docs/phase-roadmap.md) — A6 阶段路线
- [docs/observability.md](./docs/observability.md) — A8 可观测性
- [docs/deployment.md](./docs/deployment.md) — A9 部署与运维
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

## 致谢

- [agent-loop-scaffold](https://github.com/hyqskevin/agent-loop-scaffold) — 8 步 loop 标准
- [Nuxt UI](https://ui.nuxt.com) — Vue 组件库
- [Google design.md](https://github.com/google-labs-code/design.md) — design token 规范