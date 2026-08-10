# A8 可观测性 — ai-github-radar

> 日志 / 指标 / 告警。阶段一单机优先，结构化日志 + 关键事件计数。

## 日志

### 库

- `loguru`：单文件、彩色、自动 rotation
- 输出格式：JSON（生产）/ 文本（开发）
- 文件：`./data/radar.log`
- rotation：100 MB × 5
- retention：30 天

### 级别

| 级别 | 用途 | 示例 |
|---|---|---|
| DEBUG | 单条 API 调用的完整请求/响应 | "GET /user/starred?page=3 → 200 (1.2s)" |
| INFO | 业务事件 | "init: 拉取 507 个 star", "scan: 推送 12 条到 feishu" |
| WARNING | 可恢复异常 | "Trending 页面解析失败，fallback 到 search API" |
| ERROR | 用户能感知的失败 | "GitHub 401: token 无效" |
| CRITICAL | 进程崩溃 | DB 写失败 + 重试 3 次仍失败 |

### 结构化字段

```json
{
  "ts": "2026-08-10T14:23:45Z",
  "level": "INFO",
  "event": "scan.complete",
  "duration_ms": 4321,
  "trending_count": 50,
  "matched_count": 12,
  "pushed_count": 12,
  "channel": "feishu",
  "user": "hyqskevin"
}
```

## 指标（阶段一）

不引入 Prometheus / OpenTelemetry，单机不需要。

关键计数写到 SQLite `metrics` 表（可选）：

```sql
CREATE TABLE metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  event TEXT NOT NULL,        -- "scan.complete" / "keyword.add" / ...
  payload TEXT                -- JSON
);
```

CLI 一行查看：`ai-github-radar metrics --today`。

## 告警（阶段一：无）

阶段一无外部告警。错误写到日志 + stderr。

## 关键事件清单

| 事件 | 触发 | 关键字段 |
|---|---|---|
| `init.start` / `init.complete` | init 命令 | user, star_count, kw_count |
| `scan.start` / `scan.complete` | scan 命令 | duration, trending_count, matched_count, pushed_count |
| `keyword.add/del/toggle` | keyword 子命令 | term, source |
| `github.api.error` | 任何 GitHub API 失败 | status_code, endpoint, retry |
| `push.error` | 推送失败 | channel, error |

## 测试覆盖

- [ ] `tests/observability/test_logging.py` — 日志格式 + rotation
- [ ] `tests/observability/test_metrics.py` — 关键事件入库
- [ ] `tests/e2e/test_full_flow.py` — 跑通完整闭环时日志条数对齐