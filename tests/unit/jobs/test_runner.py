"""tests/unit/jobs/test_runner.py — runner submit_task + finish_job DB write."""

from __future__ import annotations

import threading
import time
from unittest.mock import patch

import pytest

from ai_github_radar.db.models import Job
from ai_github_radar.storage.db import session_scope
from ai_github_radar.jobs.runner import run_summarize, submit_task


@pytest.fixture()
def db(tmp_path):
    """用 temp file SQLite + NullPool(每个 session 独立 connection)。

    SQLite + 多 thread 用 file-based db + NullPool 比 StaticPool 更稳定。
    """
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool
    from sqlalchemy.orm import sessionmaker
    from ai_github_radar import storage
    from ai_github_radar.db import Base

    db_path = tmp_path / "test_radar.db"
    db_url = f"sqlite:///{db_path}"
    mem_engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    Base.metadata.create_all(mem_engine)

    storage.db._engine = mem_engine
    storage.db._factory = sessionmaker(bind=mem_engine, expire_on_commit=False)

    Session = sessionmaker(bind=mem_engine)
    s = Session()
    yield s
    s.close()
    storage.db.reset_for_testing()
    if db_path.exists():
        db_path.unlink()


def _wait_for_job(job_id: int, timeout: float = 5.0) -> Job:
    """等 job 到终态,返 Job 实例(在 session_scope 内访问字段)。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with session_scope() as s:
            j = s.get(Job, job_id)
            if j and j.status in ("success", "failed"):
                # 把字段 copy 到一个普通 dict-like 防止 DetachedInstance
                # 直接 return Job 但访问 attribute 必须在 with 内
                return j
        time.sleep(0.1)
    raise TimeoutError(f"job #{job_id} didn't finish in {timeout}s")


class _JobSnapshot:
    """轻量包装 Job,让 field 访问不需 attached session。"""

    def __init__(self, j: Job) -> None:
        self.id = j.id
        self.name = j.name
        self.status = j.status
        self.started_at = j.started_at
        self.finished_at = j.finished_at
        self.duration_ms = j.duration_ms
        self.error = j.error
        self.result = j.result
        self.payload = j.payload


def test_submit_success_writes_status(db):
    with session_scope() as s:
        future, job_id = submit_task("test", s, lambda: {"count": 3})
    future.result(timeout=5)
    final = _wait_for_job(job_id)
    assert final.status == "success"
    assert final.finished_at is not None
    assert final.duration_ms is not None
    assert final.duration_ms >= 0


def test_submit_failure_writes_error(db):
    def boom():
        raise RuntimeError("explosion")

    with session_scope() as s:
        future, job_id = submit_task("test", s, boom)
    future.result(timeout=5)
    final = _wait_for_job(job_id)
    assert final.status == "failed"
    assert final.error is not None
    assert "RuntimeError" in final.error
    assert "explosion" in final.error


def test_submit_returns_dict_result(db):
    with session_scope() as s:
        future, job_id = submit_task("test", s, lambda: {"stars": 50, "kws": 12})
    future.result(timeout=5)
    final = _wait_for_job(job_id)
    assert final.status == "success"
    import json
    assert json.loads(final.result) == {"stars": 50, "kws": 12}


def test_submit_kwargs_passed(db):
    """kwargs 应传给 fn + 写进 payload."""
    with session_scope() as s:
        future, job_id = submit_task("kwarg_test", s, lambda x, y: x + y, x=10, y=20)
    future.result(timeout=5)
    final = _wait_for_job(job_id)
    import json
    assert json.loads(final.payload) == {"x": 10, "y": 20}


def test_submit_multiple_concurrent(db):
    """3 个并发 job,都应 mark success。"""
    with session_scope() as s:
        f1, j1 = submit_task("a", s, lambda: 1)
        f2, j2 = submit_task("b", s, lambda: 2)
        f3, j3 = submit_task("c", s, lambda: 3)
    f1.result(timeout=5)
    f2.result(timeout=5)
    f3.result(timeout=5)
    for jid in (j1, j2, j3):
        f = _wait_for_job(jid)
        assert f.status == "success"


# ---------------------------------------------------------------------------
# run_summarize (T137)
# ---------------------------------------------------------------------------


def test_run_summarize_invalid_scope_raises(db):
    from ai_github_radar.llm.summarizer import LLMProviderError
    with pytest.raises(ValueError):
        run_summarize(scope="bogus")


def test_run_summarize_stars_sets_summary(db):
    from ai_github_radar.db.models import Star
    from ai_github_radar.llm.summarizer import SummaryResult

    with session_scope() as s:
        star = Star(
            repo_id=1, owner="o", name="r", full_name="o/r",
            description="async web framework", language="python",
            topics='["web"]',
        )
        s.add(star)
        s.commit()
        star_id = star.id

    fake = SummaryResult("一个异步 Web 框架", "openai/test")
    with patch(
        "ai_github_radar.llm.summarizer.summarize_repo", return_value=fake
    ) as mocked:
        result = run_summarize(scope="stars", only_missing=True, limit=10)

    assert mocked.called
    assert result["processed"] == 1
    with session_scope() as s:
        row = s.get(Star, star_id)
        assert row.summary == "一个异步 Web 框架"
        assert row.summary_model == "openai/test"
        assert row.summary_at is not None


def test_run_summarize_keywords_sets_rationale(db):
    from ai_github_radar.db.models import Keyword

    with session_scope() as s:
        kw = Keyword(term="agent", weight=5.0, source="auto")
        s.add(kw)
        s.commit()
        kw_id = kw.id

    with patch(
        "ai_github_radar.llm.summarizer.explain_keyword",
        return_value="用户关注 agent 生态",
    ) as mocked:
        result = run_summarize(scope="keywords", only_missing=True, limit=10)

    assert mocked.called
    assert result["processed"] == 1
    with session_scope() as s:
        row = s.get(Keyword, kw_id)
        assert row.rationale == "用户关注 agent 生态"


def test_run_summarize_stars_counts_failures(db):
    """个别 star 摘要失败 → failed 计数 + 错误记录,不中断。"""
    from ai_github_radar.db.models import Star
    from ai_github_radar.llm.summarizer import LLMProviderError, SummaryResult

    with session_scope() as s:
        s.add(Star(repo_id=1, owner="o", name="a", full_name="o/a"))
        s.add(Star(repo_id=2, owner="o", name="b", full_name="o/b"))
        s.commit()

    def fake(*args, **kwargs):
        raise LLMProviderError("provider down")

    with patch("ai_github_radar.llm.summarizer.summarize_repo", side_effect=fake):
        result = run_summarize(scope="stars", only_missing=True, limit=10)

    assert result["processed"] == 0
    assert result["failed"] == 2
    assert len(result["errors"]) == 2
    assert any("provider down" in e for e in result["errors"])