"""T006 repository.py Keyword CRUD 测试。

用 in-memory SQLite,真实 ORM,不走 mock。
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from ai_github_radar.db import Base
from ai_github_radar.db.models import Keyword
from ai_github_radar.keywords.repository import KeywordRepository


@pytest.fixture()
def session():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    factory = sessionmaker(bind=eng)
    s = factory()
    try:
        yield s
    finally:
        s.close()
        eng.dispose()


def _now() -> str:
    return datetime.utcnow().isoformat()


def test_ac7_list_returns_all_keywords(session) -> None:
    """AC-7: list() 返回所有关键字。"""
    session.add(Keyword(term="agent", created_at=_now(), updated_at=_now()))
    session.add(Keyword(term="mcp", created_at=_now(), updated_at=_now()))
    session.commit()
    repo = KeywordRepository(session)
    items = repo.list()
    assert {k.term for k in items} == {"agent", "mcp"}


def test_ac8_list_enabled_only_filters(session) -> None:
    """AC-8: list(enabled_only=True) 过滤 enabled=False。"""
    session.add(Keyword(term="a", enabled=True, created_at=_now(), updated_at=_now()))
    session.add(Keyword(term="b", enabled=False, created_at=_now(), updated_at=_now()))
    session.add(Keyword(term="c", enabled=True, created_at=_now(), updated_at=_now()))
    session.commit()
    repo = KeywordRepository(session)
    items = repo.list(enabled_only=True)
    assert {k.term for k in items} == {"a", "c"}


def test_ac9_upsert_updates_existing(session) -> None:
    """AC-9: upsert 已存在则更新 weight。"""
    repo = KeywordRepository(session)
    repo.upsert("agent", weight=1.0)
    session.commit()
    repo.upsert("agent", weight=5.0)  # 已存在,更新 weight
    session.commit()
    got = repo.get_by_term("agent")
    assert got is not None
    assert got.weight == 5.0


def test_ac10_add_raises_on_duplicate(session) -> None:
    """AC-10: add 已存在 term 抛 IntegrityError。"""
    repo = KeywordRepository(session)
    repo.add("agent")
    session.commit()
    with pytest.raises(IntegrityError):
        repo.add("agent")
        session.commit()


def test_ac11_delete_existing_returns_true(session) -> None:
    """AC-11: delete(term) 存在返回 True。"""
    repo = KeywordRepository(session)
    repo.add("agent")
    session.commit()
    assert repo.delete("agent") is True
    session.commit()
    assert repo.get_by_term("agent") is None


def test_ac12_delete_nonexistent_returns_false(session) -> None:
    """AC-12: delete 不存在返 False。"""
    repo = KeywordRepository(session)
    assert repo.delete("never_existed") is False


def test_ac13_toggle_flips_enabled(session) -> None:
    """AC-13: toggle 翻转 enabled。"""
    repo = KeywordRepository(session)
    repo.add("agent", source="manual")
    session.commit()
    k1 = repo.toggle("agent")
    session.commit()
    assert k1 is not None and k1.enabled is False
    k2 = repo.toggle("agent")
    session.commit()
    assert k2 is not None and k2.enabled is True


def test_ac14_bulk_upsert_count(session) -> None:
    """AC-14: bulk_upsert_from_tfidf 返回 upsert 数量。"""
    repo = KeywordRepository(session)
    results = [
        ("agent", 0.8),
        ("claude", 0.7),
        ("mcp", 0.6),
    ]
    n = repo.bulk_upsert_from_tfidf(results)
    session.commit()
    assert n == 3
    assert {k.term for k in repo.list()} == {"agent", "claude", "mcp"}


def test_bulk_upsert_weight_normalized(session) -> None:
    """weight 归一化到 1.0-10.0(weight * 10,封顶 10)。"""
    repo = KeywordRepository(session)
    repo.bulk_upsert_from_tfidf([("a", 0.1), ("b", 0.5), ("c", 1.5)])
    session.commit()
    a = repo.get_by_term("a")
    b = repo.get_by_term("b")
    c = repo.get_by_term("c")
    assert a.weight == 1.0  # 0.1 * 10 = 1.0
    assert b.weight == 5.0
    assert c.weight == 10.0  # 1.5 * 10 = 15 → 封顶 10


def test_get_by_id(session) -> None:
    """get_by_id 找到。"""
    repo = KeywordRepository(session)
    k = repo.add("agent", source="manual")
    session.commit()
    got = repo.get_by_id(k.id)
    assert got is not None
    assert got.term == "agent"


def test_toggle_nonexistent_returns_none(session) -> None:
    """toggle 不存在 term 返 None。"""
    repo = KeywordRepository(session)
    assert repo.toggle("never_existed") is None


def test_ac15_init_flow_50_stars_yields_30_keywords(session) -> None:
    """AC-15: 50 个真实化 star → TF-IDF + bulk_upsert → ≥ 30 keywords。"""
    from ai_github_radar.keywords.extractor import extract_keywords_tf_idf

    # 构造 50 个"star dict" 风格的描述
    star_dicts = []
    topics_pool = [
        ["python", "web", "api"],
        ["rust", "async", "runtime"],
        ["python", "ml", "ai"],
        ["typescript", "react", "frontend"],
        ["go", "kubernetes", "cloud"],
        ["python", "data", "pandas"],
        ["rust", "embedded", "no-std"],
        ["python", "fastapi", "async"],
        ["javascript", "node", "web"],
        ["rust", "cli", "tools"],
    ]
    descriptions = [
        "Python web framework for building APIs with FastAPI support and async runtime",
        "Rust async runtime for high-performance networking applications and IO",
        "Python machine learning library with deep learning neural networks and AI",
        "TypeScript React framework for frontend web applications with components",
        "Go Kubernetes operator for cloud native deployment and orchestration",
        "Python data science toolkit with pandas numpy scikit-learn analysis",
        "Rust embedded systems development with no_std and async runtime support",
        "Python FastAPI web framework for async APIs with authentication",
        "JavaScript Node.js backend framework for web applications and APIs",
        "Rust CLI tools for command line developer productivity and scripting",
    ]
    for i in range(50):
        star_dicts.append({
            "description": descriptions[i % 10],
            "topics": topics_pool[i % 10],
            "language": "Python" if i % 2 == 0 else "Rust",
        })

    # 把 dict 拼成文本喂给 TF-IDF
    docs = []
    for sd in star_dicts:
        parts = [sd.get("description") or "", sd.get("language") or ""]
        parts.extend(sd.get("topics") or [])
        docs.append(" ".join(parts))

    tfidf_results = extract_keywords_tf_idf(docs, top_n=50, min_df=2, ngram_range=(1, 2))
    repo = KeywordRepository(session)
    n = repo.bulk_upsert_from_tfidf(tfidf_results)
    session.commit()
    assert n >= 30, f"expected ≥30 keywords, got {n} from {len(tfidf_results)} TF-IDF results"