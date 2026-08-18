"""T003 模型表结构 + 唯一约束测试。"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError

from ai_github_radar.db import Base
from ai_github_radar.db.models import Keyword, Recommendation, Star, TrendingSnapshot


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


def test_ac1_four_tables_created(engine) -> None:
    """AC-1: 4 张表存在。"""
    insp = inspect(engine)
    names = set(insp.get_table_names())
    assert {"stars", "keywords", "trending_snapshots", "recommendations"} <= names


def test_ac5_stars_repo_id_unique(engine) -> None:
    """AC-5: stars.repo_id UNIQUE。"""
    from sqlalchemy.orm import Session

    with Session(engine) as s:
        s.add(Star(repo_id=1, owner="o", name="n", full_name="o/n", fetched_at="2026-01-01"))
        s.commit()
    with Session(engine) as s:
        s.add(Star(repo_id=1, owner="o2", name="n2", full_name="o2/n2", fetched_at="2026-01-01"))
        with pytest.raises(IntegrityError):
            s.commit()


def test_ac6_keyword_term_unique(engine) -> None:
    """AC-6: keywords.term UNIQUE。"""
    from sqlalchemy.orm import Session

    with Session(engine) as s:
        s.add(Keyword(term="agent", created_at="2026-01-01", updated_at="2026-01-01"))
        s.commit()
    with Session(engine) as s:
        s.add(Keyword(term="agent", created_at="2026-01-02", updated_at="2026-01-02"))
        with pytest.raises(IntegrityError):
            s.commit()


def test_ac7_trending_unique_pair(engine) -> None:
    """AC-7: trending_snapshots UNIQUE(repo_id, snapshot_date)。"""
    from sqlalchemy.orm import Session

    with Session(engine) as s:
        s.add(TrendingSnapshot(repo_id=42, snapshot_date="2026-08-18", rank=1, fetched_at="2026-08-18"))
        s.commit()
    with Session(engine) as s:
        s.add(TrendingSnapshot(repo_id=42, snapshot_date="2026-08-18", rank=2, fetched_at="2026-08-18"))
        with pytest.raises(IntegrityError):
            s.commit()


def test_ac8_recommendation_unique_pair(engine) -> None:
    """AC-8: recommendations UNIQUE(repo_id, pushed_at)。"""
    from sqlalchemy.orm import Session

    with Session(engine) as s:
        s.add(Recommendation(repo_id=7, score=8.5, channel="local", pushed_at="2026-08-18T10:00:00"))
        s.commit()
    with Session(engine) as s:
        s.add(Recommendation(repo_id=7, score=7.0, channel="local", pushed_at="2026-08-18T10:00:00"))
        with pytest.raises(IntegrityError):
            s.commit()


def test_c7_columns_match_ddl(engine) -> None:
    """C7: ORM 字段 == DDL 列(按 docs/database-design.md)。"""
    insp = inspect(engine)
    star_cols = {c["name"] for c in insp.get_columns("stars")}
    expected = {
        "id",
        "repo_id",
        "owner",
        "name",
        "full_name",
        "description",
        "language",
        "topics",
        "homepage",
        "stargazers_count",
        "pushed_at",
        "starred_at",
        "fetched_at",
        "archived",
    }
    assert expected <= star_cols


def test_c10_indexes_exist(engine) -> None:
    """C10: 关键索引存在(stars.language / stars.fetched_at / keywords.enabled)。"""
    insp = inspect(engine)
    star_idx_names = {i["name"] for i in insp.get_indexes("stars")}
    kw_idx_names = {i["name"] for i in insp.get_indexes("keywords")}
    # stars.language 索引(Language 字段 Mapped 上 index=True 自动生成)
    assert any("language" in n.lower() for n in star_idx_names)
    # stars.fetched_at 索引(同上)
    assert any("fetched" in n.lower() for n in star_idx_names)
    # keywords.enabled 索引
    assert any("enabled" in n.lower() for n in kw_idx_names)