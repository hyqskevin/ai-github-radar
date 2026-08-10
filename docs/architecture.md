# A5 架构决策记录 (ADR)

> 项目级架构决策。每个 ADR 一条，决定要带原因 + 替代方案。

## ADR 001 — Python 单语言 vs 多语言

**日期**：2026-08-10
**状态**：已采纳

**背景**：ai-github-radar 是 CLI 工具，候选实现：
- (a) 纯 Python
- (b) Python（CLI）+ Node（trending 解析）
- (c) Go

**决策**：纯 Python 3.12。

**原因**：
- GitHub API client / TF-IDF / LLM SDK / SQLite 都 Python 原生支持最齐
- 与 agent-loop-scaffold 锁定栈一致（uv + .venv）
- 用户已熟悉 Python（agent-loop-scaffold 8 必填文档强 Python 倾向）

**替代方案被拒**：
- (b) Node trending 解析 — 收益小（页面不常改），引入 Node 工具链成本高
- (c) Go — 编译型 CLI 启动快，但对个人开发者打包 / 分发不友好

---

## ADR 002 — TF-IDF + 可选 LLM

**日期**：2026-08-10
**状态**：已采纳

**背景**：关键字提取有两条路：
- (a) 纯 TF-IDF（基于 stars 描述 + topics）
- (b) 直接用 LLM 总结

**决策**：默认 TF-IDF，LLM 作为可选升级。

**原因**：
- TF-IDF：零外部依赖、零成本、可解释（可以看权重最高的 term）
- LLM：能识别语义聚类（"agent" 和 "Claude Code" 是同一类），但成本 + 延迟
- 阶段一用户先跑 TF-IDF 试，对结果不满意再开 LLM

**触发升级**：`.env` 配 `OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY`，init 自动用 LLM。

**替代方案被拒**：
- 只用 LLM — 默认依赖外部 API，门槛太高
- 只用 TF-IDF — 对小样本（< 100 star）效果差，LLM 是补救

---

## ADR 003 — 阶段一无 HTTP API

**日期**：2026-08-10
**状态**：已采纳

**背景**：是否暴露 FastAPI/HTTP 服务？

**决策**：阶段一**不暴露** HTTP API，只有 CLI。

**原因**：
- 阶段一目标用户是开发者本人，单机单用户
- CLI 触发 + 推送 + 历史回顾就够了
- 加 HTTP API = 加一层攻击面 + 部署复杂度

**替代方案被拒**：
- FastAPI + uvicorn — 阶段一不需要
- MCP server — 等有需求再加（阶段二）

---

## ADR 004 — 推送走 webhook / SMTP，不走 IM SDK

**日期**：2026-08-10
**状态**：已采纳

**背景**：推送目标候选：
- (a) 飞书 webhook / SMTP 邮件（轻）
- (b) 飞书 SDK / 微信 wechaty / 钉钉 SDK（重）
- (c) 本地文件 / macOS Notification Center

**决策**：(a) + (c)。三种 target 切换：`local` / `feishu` / `email`。

**原因**：
- webhook / SMTP 是无状态协议，不需要 OAuth、长连接、登录态
- 避免依赖 Wechaty / 钉钉 SDK 这种需要扫码登录的复杂库
- 本地文件最稳，调试和审计首选

**替代方案被拒**：
- (b) — 依赖重、维护成本高、登录态脆弱

---

## ADR 005 — 周期任务用 asyncio 守护进程，不用 celery

**日期**：2026-08-10
**状态**：已采纳

**背景**：周期任务候选：
- (a) asyncio 守护进程（前台跑，launchd 管）
- (b) Celery + Redis
- (c) APScheduler in-process

**决策**：(a) asyncio daemon + 外部 launchd。

**原因**：
- 阶段一只有一个周期任务（scan），杀鸡用牛刀没必要
- Celery + Redis = 多一个进程 + 多一个 broker
- launchd 已经是 macOS 标配，重启、开机自启、日志都现成

**替代方案被拒**：
- (b) Celery — 过度工程
- (c) APScheduler — 进程死了不自动拉起（daemon 模式又跟 a 重复）