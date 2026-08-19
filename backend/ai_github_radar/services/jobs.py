"""services/jobs.py — 任务执行记录 (T127).

提供:
- start_job(name, payload): 新建 pending→running 记录
- finish_job(job, result, error=None): 改成 success/failed
- recent_jobs(limit): 最近 N 条(给前端 /api/jobs 用)
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from ai_github_radar.db.models import Job


def _utcnow() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def start_job(s: Session, name: str, payload: Optional[dict] = None) -> Job:
    """新建 + 立即标 running。"""
    j = Job(
        name=name,
        status="running",
        started_at=_utcnow(),
        payload=json.dumps(payload, ensure_ascii=False) if payload else None,
    )
    s.add(j)
    s.flush()
    return j


def finish_job(
    s: Session,
    job: Job,
    result: Optional[dict] = None,
    error: Optional[str] = None,
) -> Job:
    """标 success / failed,记录 duration_ms。"""
    finished_at = _utcnow()
    started = datetime.fromisoformat(job.started_at)
    end = datetime.fromisoformat(finished_at)
    duration_ms = int((end - started).total_seconds() * 1000)
    job.finished_at = finished_at
    job.duration_ms = duration_ms
    job.result = json.dumps(result, ensure_ascii=False) if result else None
    job.error = error
    job.status = "failed" if error else "success"
    s.flush()
    return job


def recent_jobs(s: Session, limit: int = 50) -> list[Job]:
    return (
        s.query(Job)
        .order_by(Job.started_at.desc())
        .limit(limit)
        .all()
    )


def job_to_dict(j: Job) -> dict:
    """序列化单条 Job 给 API。"""
    out = {
        "id": j.id,
        "name": j.name,
        "status": j.status,
        "started_at": j.started_at,
        "finished_at": j.finished_at,
        "duration_ms": j.duration_ms,
    }
    # JSON 字段尝试解,失败保留原文
    if j.payload:
        try:
            out["payload"] = json.loads(j.payload)
        except (json.JSONDecodeError, TypeError):
            out["payload"] = j.payload
    if j.result:
        try:
            out["result"] = json.loads(j.result)
        except (json.JSONDecodeError, TypeError):
            out["result"] = j.result
    if j.error:
        out["error"] = j.error
    return out