"""in-process 周期调度器 — T015.

不依赖 APScheduler,用 threading.Event + time.sleep。
前台阻塞跑,stop_event.set() 退出。
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

log = logging.getLogger(__name__)


def run_once(
    push_target: str = "local",
    top: int = 10,
    language: Optional[str] = None,
    since: str = "daily",
    min_score: float = 0.0,
    *,
    output_file: Optional[str] = None,
    stdout: bool = False,
) -> int:
    """执行一次 scan。返回 recs 数量(失败返 -1)。

    复用 cli.scan_cmd.do_scan。
    """
    import ai_github_radar.cli.scan_cmd as _scan_mod
    recs = _scan_mod.do_scan(
        push_target=push_target,
        top=top,
        language=language,
        since=since,
        min_score=min_score,
        output_file=output_file,
        stdout=stdout,
        echo=lambda msg: log.info(msg),
    )
    if recs is None:
        return -1
    return len(recs)


def run_forever(
    interval_seconds: int = 86400,  # 默认 24h
    push_target: str = "local",
    top: int = 10,
    *,
    language: Optional[str] = None,
    since: str = "daily",
    min_score: float = 0.0,
    stop_event: Optional[threading.Event] = None,
) -> None:
    """阻塞跑:每 N 秒 run_once 一次,stop_event.set() 时退出。

    单次 run_once 抛错不退出 daemon,只 log warning。
    """
    event = stop_event or threading.Event()
    log.info(
        f"scheduler started: interval={interval_seconds}s, push={push_target}, top={top}"
    )
    # 第一次立即跑(可选,但保持简单:先 sleep 再跑,避免冷启动网络报错连击)
    while not event.is_set():
        # sleep 可被 set() 唤醒
        if event.wait(timeout=interval_seconds):
            break
        try:
            n = run_once(
                push_target=push_target,
                top=top,
                language=language,
                since=since,
                min_score=min_score,
            )
            log.info(f"scan completed: {n} recommendations")
        except Exception as e:
            log.exception(f"scan failed, continuing: {e}")
    log.info("scheduler stopped")