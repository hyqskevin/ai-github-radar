"""services/schedules.py — 定时任务 CRUD (T128).

设计:
- 用 cron 表达式(5 段 unix cron)
- 内存中跑 APScheduler 或简单 sleep-loop(阶段二用 APScheduler)
- 现在:T125 只暴露 CRUD;调度逻辑在 jobs/scheduler.py 里
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ai_github_radar.db.models import Schedule


def _utcnow() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def list_schedules(s: Session) -> list[Schedule]:
    return s.query(Schedule).order_by(Schedule.id.asc()).all()


def get_schedule(s: Session, schedule_id: int) -> Optional[Schedule]:
    return s.get(Schedule, schedule_id)


def create_schedule(
    s: Session,
    name: str,
    cron: str,
    enabled: bool = True,
    payload: Optional[dict] = None,
) -> Schedule:
    sched = Schedule(
        name=name,
        cron=cron,
        enabled=enabled,
        payload=json.dumps(payload, ensure_ascii=False) if payload else None,
        created_at=_utcnow(),
    )
    s.add(sched)
    s.flush()
    return sched


def update_schedule(
    s: Session,
    schedule_id: int,
    cron: Optional[str] = None,
    enabled: Optional[bool] = None,
    payload: Optional[dict] = None,
) -> Optional[Schedule]:
    sched = s.get(Schedule, schedule_id)
    if sched is None:
        return None
    if cron is not None:
        sched.cron = cron
    if enabled is not None:
        sched.enabled = enabled
    if payload is not None:
        sched.payload = json.dumps(payload, ensure_ascii=False)
    s.flush()
    return sched


def delete_schedule(s: Session, schedule_id: int) -> bool:
    sched = s.get(Schedule, schedule_id)
    if sched is None:
        return False
    s.delete(sched)
    s.flush()
    return True


def schedule_to_dict(sc: Schedule) -> dict:
    out = {
        "id": sc.id,
        "name": sc.name,
        "cron": sc.cron,
        "enabled": sc.enabled,
        "last_run_at": sc.last_run_at,
        "next_run_at": sc.next_run_at,
        "created_at": sc.created_at,
    }
    if sc.payload:
        try:
            out["payload"] = json.loads(sc.payload)
        except (json.JSONDecodeError, TypeError):
            out["payload"] = sc.payload
    return out