# INSTALL.md — ai-github-radar 安装指引

> 跨平台安装。**macOS / Linux 直接走；Windows 建议 WSL2**。

## 前置依赖

- Python 3.12（项目锁在 `.python-version`）
- Node 22（可选，仅 IDE hook 需要）
- GitHub Personal Access Token（PAT）
  - https://github.com/settings/tokens/new?scopes=public_repo&description=ai-github-radar
  - 只勾 `public_repo` 即可（不需要私有仓库权限）

## 步骤

### 1. 克隆

```bash
git clone https://github.com/hyqskevin/ai-github-radar.git
cd ai-github-radar
```

### 2. 装 Python 环境（uv + .venv）

```bash
bash scripts/setup-python.sh
```

该脚本会：
- 校验 uv 安装
- 在项目内建 `.venv/`
- 装所有依赖
- 锁死 6 个环境变量到项目目录（UV_CACHE_DIR / PIP_CACHE_DIR 等）

### 3. 装 Node 环境（可选）

```bash
bash scripts/setup-node.sh
```

仅 IDE hook（Claude Code / Cursor）需要。

### 4. 配 `.env`

```bash
cp config/.env.example .env
nano .env  # 或 vim
```

必填：

```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxx
RADAR_USER=hyqskevin
```

可选：

```bash
RADAR_FETCH_INTERVAL=daily       # daily | weekly
RADAR_PUSH_TARGET=local          # local | feishu | email
RADAR_DB_PATH=./data/radar.db
RADAR_LOG_LEVEL=INFO

# 飞书推送（可选）
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx

# 邮件推送（可选）
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=app_password
EMAIL_TO=you@gmail.com

# LLM 升级（可选）
OPENAI_API_KEY=sk-xxx            # 用 LLM 提关键字时填
ANTHROPIC_API_KEY=sk-ant-xxx
```

### 5. 首次运行

```bash
# 拉你的 star + 提关键字
uv run python -m ai_github_radar.cli init

# 看提取的关键字
uv run python -m ai_github_radar.cli keyword list

# 单次扫描
uv run python -m ai_github_radar.cli scan

# 周期守护（前台）
uv run python -m ai_github_radar.cli daemon
```

### 6. （推荐）装 IDE hook

```bash
node scripts/sync-runtimes.mjs
```

注册到 `.claude/` / `.codex/` / `.cursor/` / `.hermes/` / `openclaw/`。

## 卸载

```bash
# 清本地
cd ..
rm -rf ai-github-radar

# 清环境变量（如果 setup-*.sh 写到了 shell config）
# 检查 ~/.zshrc / ~/.bashrc 里有没有 RADAR_* / GITHUB_TOKEN 字样
```

## 常见问题

### Q: Token scope 报错？

A: 必须勾 `public_repo`。如果只看自己的 star（public），这个足够。

### Q: 抓 trending 失败？

A: GitHub 改了 trending 页面结构时会失败。脚本会 fallback 到 search API（`/search/repositories?q=created:>YYYY-MM-DD&sort=stars`）。

### Q: 关键字不准？

A: 阶段一用 TF-IDF，样本少（< 100 star）时不准。手动 `keyword add` 修正。

### Q: macOS launchd 怎么配？

A: 见 `docs/scheduled-jobs.md`。