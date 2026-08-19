"""tests/unit/services/test_services.py — settings + jobs + schedules CRUD."""

from __future__ import annotations

import pytest

from ai_github_radar.db.models import Job, Schedule, Setting
from ai_github_radar.services import settings as s
from ai_github_radar.services import jobs as j
from ai_github_radar.services import schedules as sc


@pytest.fixture()
def db():
    """内存 SQLite + 临时 schema."""
    from sqlalchemy import create_engine
    from ai_github_radar.db import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=engine)
    s_ = Session()
    yield s_
    s_.close()


# ---------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------


def test_setting_get_set_str(db):
    s.set_setting(db, "llm.provider", "deepseek")
    assert s.get_setting(db, "llm.provider") == "deepseek"  # 原样存


def test_setting_get_set_dict(db):
    s.set_setting(db, "llm.model", {"name": "deepseek-chat", "temperature": 0.3})
    raw = s.get_setting(db, "llm.model")
    assert "deepseek-chat" in raw
    # 反序列化
    loaded = s.get_setting_json(db, "llm.model")
    assert loaded["name"] == "deepseek-chat"
    assert loaded["temperature"] == 0.3


def test_setting_get_default(db):
    assert s.get_setting(db, "nope") is None
    assert s.get_setting(db, "nope", "fallback") == "fallback"


def test_setting_overwrite(db):
    s.set_setting(db, "x", "v1")
    s.set_setting(db, "x", "v2")
    assert s.get_setting(db, "x") == "v2"


def test_setting_list(db):
    s.set_setting(db, "a", 1)
    s.set_setting(db, "b", 2)
    out = s.list_settings(db)
    assert "a" in out and "b" in out


# ---------------------------------------------------------------------------
# jobs
# ---------------------------------------------------------------------------


def test_job_lifecycle(db):
    job = j.start_job(db, "scan", {"top": 10})
    assert job.status == "running"
    assert job.name == "scan"
    assert job.payload and "top" in job.payload

    j.finish_job(db, job, result={"count": 5})
    assert job.status == "success"
    assert job.finished_at is not None
    assert job.duration_ms is not None
    assert job.duration_ms >= 0
    assert job.result and "count" in job.result


def test_job_failure(db):
    job = j.start_job(db, "init")
    j.finish_job(db, job, error="boom")
    assert job.status == "failed"
    assert job.error == "boom"


def test_job_recent_limit(db):
    for i in range(5):
        j.start_job(db, f"task_{i}")
    rec = j.recent_jobs(db, limit=3)
    assert len(rec) == 3


def test_job_to_dict(db):
    job = j.start_job(db, "scan", {"k": "v"})
    j.finish_job(db, job, result={"r": 1})
    d = j.job_to_dict(job)
    assert d["name"] == "scan"
    assert d["status"] == "success"
    assert d["payload"] == {"k": "v"}
    assert d["result"] == {"r": 1}


# ---------------------------------------------------------------------------
# schedules
# ---------------------------------------------------------------------------


def test_schedule_crud(db):
    created = sc.create_schedule(db, "scan_daily", "0 9 * * *")
    assert created.id is not None
    assert created.cron == "0 9 * * *"
    assert created.enabled is True

    found = sc.get_schedule(db, created.id)
    assert found is not None
    assert found.name == "scan_daily"

    all_ = sc.list_schedules(db)
    assert len(all_) == 1


def test_schedule_update(db):
    s_obj = sc.create_schedule(db, "old", "* * * * *")
    updated = sc.update_schedule(db, s_obj.id, cron="0 12 * * *", enabled=False)
    assert updated.cron == "0 12 * * *"
    assert updated.enabled is False


def test_schedule_delete(db):
    s_obj = sc.create_schedule(db, "tmp", "* * * * *")
    assert sc.delete_schedule(db, s_obj.id) is True
    assert sc.get_schedule(db, s_obj.id) is None


def test_schedule_unique_name(db):
    sc.create_schedule(db, "daily", "0 9 * * *")
    with pytest.raises(Exception):
        sc.create_schedule(db, "daily", "0 10 * * *")


def test_schedule_to_dict_with_payload(db):
    s_obj = sc.create_schedule(db, "p", "* * * * *", payload={"top": 5})
    d = sc.schedule_to_dict(s_obj)
    assert d["payload"] == {"top": 5}


def test_schedule_payload_json(db):
    s_obj = sc.create_schedule(db, "p2", "* * * * *", payload={"a": 1, "b": [1, 2]})
    d = sc.schedule_to_dict(s_obj)
    assert d["payload"] == {"a": 1, "b": [1, 2]}