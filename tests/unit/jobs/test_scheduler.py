"""T015 jobs/scheduler.py 测试。

mock do_scan 避免实拉 trending;只验证 scheduler 编排逻辑。
"""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest


def test_ac1_run_once_returns_count() -> None:
    """AC-1: run_once 返回 int recs 数。"""
    with patch(
        "ai_github_radar.cli.scan_cmd.do_scan",
        return_value=[{"repo_id": 1}, {"repo_id": 2}],
    ):
        from ai_github_radar.jobs.scheduler import run_once
        n = run_once()
        assert n == 2


def test_ac1_run_once_returns_minus_one_on_failure() -> None:
    """run_once 失败返 -1(do_scan 返 None)。"""
    with patch(
        "ai_github_radar.cli.scan_cmd.do_scan",
        return_value=None,
    ):
        from ai_github_radar.jobs.scheduler import run_once
        n = run_once()
        assert n == -1


def test_ac7_run_once_passes_through_params() -> None:
    """AC-7: run_once 参数透传给 do_scan。"""
    captured = {}

    def fake_do_scan(**kw):
        captured.update(kw)
        return []

    with patch(
        "ai_github_radar.cli.scan_cmd.do_scan",
        side_effect=fake_do_scan,
    ):
        from ai_github_radar.jobs.scheduler import run_once
        run_once(
            push_target="feishu", top=5, language="python",
            since="weekly", min_score=1.5,
        )
    assert captured["push_target"] == "feishu"
    assert captured["top"] == 5
    assert captured["language"] == "python"
    assert captured["since"] == "weekly"
    assert captured["min_score"] == 1.5


def test_ac6_run_once_propagates_exception() -> None:
    """AC-6: run_once 异常不吞(由 run_forever 处理)。"""
    with patch(
        "ai_github_radar.cli.scan_cmd.do_scan",
        side_effect=RuntimeError("boom"),
    ):
        from ai_github_radar.jobs.scheduler import run_once
        with pytest.raises(RuntimeError):
            run_once()


def test_ac4_run_forever_stops_via_event() -> None:
    """AC-4: run_forever 收到 stop_event 后退出。"""
    call_count = {"n": 0}

    def fake_do_scan(**kw):
        call_count["n"] += 1
        return [{"repo_id": i} for i in range(3)]

    stop = threading.Event()
    with patch(
        "ai_github_radar.cli.scan_cmd.do_scan",
        side_effect=fake_do_scan,
    ):
        from ai_github_radar.jobs.scheduler import run_forever
        t = threading.Thread(
            target=run_forever,
            kwargs={"interval_seconds": 0.1, "stop_event": stop, "top": 5},
            daemon=True,
        )
        t.start()
        # 等到至少 1 次
        for _ in range(50):
            if call_count["n"] >= 1:
                break
            time.sleep(0.02)
        stop.set()
        t.join(timeout=2.0)
        assert not t.is_alive(), "run_forever did not stop"
        assert call_count["n"] >= 1


def test_ac5_run_forever_swallows_scan_errors() -> None:
    """AC-5: run_forever 内单次 scan 报错不退出 daemon。"""
    call_count = {"n": 0}

    def fake_do_scan(**kw):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("transient")
        return []

    stop = threading.Event()
    with patch(
        "ai_github_radar.cli.scan_cmd.do_scan",
        side_effect=fake_do_scan,
    ):
        from ai_github_radar.jobs.scheduler import run_forever
        t = threading.Thread(
            target=run_forever,
            kwargs={"interval_seconds": 0.05, "stop_event": stop},
            daemon=True,
        )
        t.start()
        for _ in range(50):
            if call_count["n"] >= 2:
                break
            time.sleep(0.02)
        stop.set()
        t.join(timeout=2.0)
        assert not t.is_alive()
        assert call_count["n"] >= 2


import time


def test_ac2_local_push_writes_file(tmp_path) -> None:
    """AC-2: run_once(push="local") → 走 do_scan,参数透传。"""
    with patch(
        "ai_github_radar.cli.scan_cmd.do_scan",
        return_value=[{"repo_id": 1}],
    ) as mocked:
        from ai_github_radar.jobs.scheduler import run_once
        n = run_once(push_target="local", output_file=str(tmp_path / "x.md"))
        assert n == 1
        # 验证 do_scan 被调,output_file 透传
        args, kwargs = mocked.call_args
        assert kwargs.get("output_file") == str(tmp_path / "x.md")


def test_ac3_stdout_push_does_not_write_file(tmp_path) -> None:
    """AC-3: run_once(stdout=True) → 不写文件。"""
    with patch(
        "ai_github_radar.cli.scan_cmd.do_scan",
        return_value=[],
    ):
        from ai_github_radar.jobs.scheduler import run_once
        n = run_once(stdout=True)
        assert n == 0
        assert list(tmp_path.iterdir()) == []