# Spec — T015 jobs/scheduler.py

| 维度 | 内容 |
|---|---|
| **TODO ID** | T015（docs/TODO.md §CLI + 周期） |
| **作者** | ai-github-radar 维护者 + AI 助手（2026-08-19） |
| **优先级** | 高 — 阶段一交付的核心场景 |
| **触发** | docs/TODO.md T015（合并 T014 launchd / systemd 思路） |

---

## B1. 设计

### 1.1 目标

实现 `src/ai_github_radar/jobs/scheduler.py`,**in-process 周期调度**:

- 用 Python 标准库 `threading` + `time.sleep` 实现**前台阻塞调度器**(不依赖 APScheduler 第三方)
- 每 N 秒(或 cron-like)调 `scan_cmd` 核心逻辑
- 暴露 `run_forever()` / `run_once()` API

### 1.2 API

```python
def run_once(
    push_target: str = "local",
    top: int = 10,
    language: str | None = None,
    since: str = "daily",
    min_score: float = 0.0,
) -> int:
    """执行一次 scan。返回 recs 数量。
    复用 cli/scan_cmd 内部逻辑(提一个公共函数)。
    """

def run_forever(
    interval_seconds: int = 86400,  # 默认 24h
    push_target: str = "local",
    top: int = 10,
    *,
    stop_event: threading.Event | None = None,
) -> None:
    """阻塞跑:每 N 秒 run_once 一次。
    stop_event.set() 时退出。
    """
```

### 1.3 非目标

- ❌ APScheduler / 分布式调度
- ❌ 多进程(单进程内 threading)
- ❌ cron-like 表达式(本 TODO 只支持固定间隔,launchd/systemd 阶段二做精确时刻调度)

---

## B2. 验收

| AC | 断言 | 怎么验 |
|---|---|---|
| AC-1 | `run_once` 返回 int recs 数量 | 单测 |
| AC-2 | `run_once(push="local")` 写文件 | tmp_path 验证 |
| AC-3 | `run_once(push="stdout")` 不写文件 | tmp_path 验证 |
| AC-4 | `run_forever` 至少调 1 次 run_once 后 stop | 单测:1s 间隔,0.5s 后 set stop |
| AC-5 | `run_forever(stop_event=...)` 退出干净 | 单测 |
| AC-6 | run_once 异常 → 抛错不退出 daemon | 单测 |
| AC-7 | 配置 (push / top / language / since / min_score) 透传 | 单测 |

---

## B3. 测试矩阵

| C | 维度 | 覆盖 |
|---|---|---|
| C1 功能 | 返回 recs 数 | AC-1 |
| C2 推送 | local 写文件 | AC-2 |
| C3 推送 | stdout 不写 | AC-3 |
| C4 调度 | run_forever 间隔 | AC-4 / AC-5 |
| C5 错误 | run_once 异常 | AC-6 |
| C6 配置 | 参数透传 | AC-7 |

测试文件：`tests/unit/jobs/test_scheduler.py`

---

## B4. 风险

- **R1**：测试 sleep 太慢 → 用 `threading.Event` + 短间隔(0.1s)加速。
- **R2**：scheduler 与 cli/scan_cmd 复用 → 提一个公共函数 `_do_scan()`。
- **R3**：DB session 跨线程要 reset_for_testing。