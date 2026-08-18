"""T014 storage 测试。"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ai_github_radar.db import Base
from ai_github_radar.storage.repositories import (
    KeywordRepository,
    RecommendationRepository,
    StarRepository,
    TrendingSnapshotRepository,
)


@pytest.fixture()
def session():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    factory = sessionmaker(bind=eng, expire_on_commit=False)
    s = factory()
    try:
        yield s
    finally:
        s.close()
        eng.dispose()


def _star_dict(repo_id: int, **kw) -> dict:
    base = {
        "repo_id": repo_id,
        "owner": f"o{repo_id}",
        "name": f"r{repo_id}",
        "full_name": f"o{repo_id}/r{repo_id}",
        "description": f"repo {repo_id}",
        "language": "Python",
        "topics": "python,fastapi",
        "homepage": None,
        "stargazers_count": 100,
        "pushed_at": "2026-08-01T00:00:00Z",
        "starred_at": "2026-08-01T00:00:00Z",
        "archived": False,
    }
    base.update(kw)
    return base


def test_star_upsert_insert_and_update(session) -> None:
    """Star upsert:不存在 → insert;存在 → update。"""
    repo = StarRepository(session)
    n1 = repo.upsert_many([_star_dict(1, stargazers_count=100)])
    session.commit()
    assert n1 == 1
    n2 = repo.upsert_many([_star_dict(1, stargazers_count=200)])
    session.commit()
    assert n2 == 1
    stars = repo.list_all()
    assert len(stars) == 1
    assert stars[0].stargazers_count == 200


def test_star_upsert_many(session) -> None:
    """批量 upsert 5 个。"""
    repo = StarRepository(session)
    n = repo.upsert_many([_star_dict(i) for i in range(5)])
    session.commit()
    assert n == 5
    assert len(repo.list_all()) == 5


def test_trending_upsert_and_list(session) -> None:
    """Trending upsert + list_by_date。"""
    repo = TrendingSnapshotRepository(session)
    snaps = [
        {"repo_id": i, "snapshot_date": "2026-08-19", "rank": i,
         "stars_today": 100 - i, "language": "Python",
         "description": f"repo {i}"}
        for i in range(1, 6)
    ]
    n = repo.upsert_many(snaps)
    session.commit()
    assert n == 5
    out = repo.list_by_date("2026-08-19")
    assert len(out) == 5
    assert out[0].rank == 1


def test_recommendation_record_and_recent(session) -> None:
    """Recommendation record + recent_repo_ids(N-day dedupe)。"""
    repo = RecommendationRepository(session)
    repo.record_push(100, score=10.0, matched_keywords=["x"], channel="local")
    repo.record_push(200, score=8.0, matched_keywords=["y"], channel="feishu")
    session.commit()
    ids = repo.recent_repo_ids(days=7)
    assert ids == {100, 200}


def test_recommendation_dedupe_window(session) -> None:
    """recent_repo_ids(days=7) 边界:8 天前的记录不返。"""
    repo = RecommendationRepository(session)
    old_time = "2026-08-01T00:00:00"  # 18 天前(相对固定 now 2026-08-19)
    repo.record_push(100, score=10.0, matched_keywords=[], channel="local",
                     pushed_at=old_time)
    session.commit()
    ids = repo.recent_repo_ids(days=7)
    assert 100 not in ids


def test_keyword_repository_through_session(session) -> None:
    """KeywordRepository(session) 仍可用(storage 子包 re-export)。"""
    from datetime import datetime
    repo = KeywordRepository(session)
    kw = repo.add("agent", weight=5.0)
    session.commit()
    assert kw.id is not None
    assert repo.get_by_term("agent") is not None