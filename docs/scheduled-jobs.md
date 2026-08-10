# A13 定时任务 — ai-github-radar

> 阶段一只有一个周期任务：`scan`（按日 / 周拉 trending 推推荐）。

## 任务清单

| ID | 名称 | 频率 | 触发命令 |
|---|---|---|---|
| `J001` | scan-and-push | daily (08:00 Asia/Shanghai) | `python -m ai_github_radar.cli scan --push $RADAR_PUSH_TARGET` |
| `J002` | cleanup-old-trending | weekly (周一 04:00) | `python -m ai_github_radar.cli cleanup --older-than 90d` |
| `J003` | refresh-stars | weekly (周日 03:00) | `python -m ai_github_radar.cli init --refresh-only` |

## 实现

阶段一**不引入** Celery / RQ / APScheduler。两种方式：

### 方式 A：内建 daemon（开发期）

```bash
python -m ai_github_radar.cli daemon --interval daily
```

前台跑，asyncio 循环。`Ctrl-C` 退出。

### 方式 B：外部调度器（生产期，推荐）

- **macOS**：launchd（plist 见 `scripts/`）
- **Linux**：systemd（service + timer 见 `scripts/`）

## 任务幂等性

每个任务必须可重入：

| 任务 | 幂等保证 |
|---|---|
| scan-and-push | `recommendations` 表 UNIQUE(repo_id, pushed_at)；同 repo 7 天内不重复推 |
| cleanup-old-trending | DELETE WHERE snapshot_date < 'YYYY-MM-DD'；无副作用 |
| refresh-stars | `stars` 表全量 UPSERT（truncate + insert）；幂等 |

## 任务超时

| 任务 | 超时 | 失败处理 |
|---|---|---|
| scan-and-push | 5 min | 退 1，外部调度器 retry 3 次（指数退避） |
| cleanup-old-trending | 30 s | 退 1，不重试（无害） |
| refresh-stars | 10 min | 退 2（GitHub 速率限制），退 1（其他），不重试 |

## 测试覆盖

- [ ] `tests/jobs/test_scan.py` — 用 respx mock GitHub，跑通完整扫描
- [ ] `tests/jobs/test_idempotency.py` — 同一 trending repo 跑两次，第二次不推
- [ ] `tests/jobs/test_cleanup.py` — 90 天前数据被清，< 90 天的保留
- [ ] `tests/jobs/test_daemon.py` — daemon 启动 → 跑一次 scan → 优雅退出