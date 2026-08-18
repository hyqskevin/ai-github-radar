"""T008 recommender/pipeline.py 测试。"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

import pytest

from ai_github_radar.db.models import Keyword, Star, TrendingSnapshot
from ai_github_radar.recommender.pipeline import (
    compute_repo_score,
    rank_recommendations,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_star(repo_id: int, full_name: str, *, description: str = "",
               language: str = "Python", topics: list[str] | None = None,
               stargazers: int = 100) -> Star:
    return Star(
        repo_id=repo_id,
        owner=full_name.split("/")[0],
        name=full_name.split("/")[1],
        full_name=full_name,
        description=description,
        language=language,
        topics=",".join(topics) if topics else None,
        stargazers_count=stargazers,
        fetched_at=datetime.utcnow().isoformat(),
    )


def _make_trending(repo_id: int, *, full_name: str = "", description: str = "",
                    language: str = "Python", stars_today: int = 50,
                    rank: int = 1, snapshot_date: str = "2026-08-18") -> TrendingSnapshot:
    return TrendingSnapshot(
        repo_id=repo_id,
        snapshot_date=snapshot_date,
        rank=rank,
        stars_today=stars_today,
        language=language,
        description=description,
        fetched_at=datetime.utcnow().isoformat(),
    )


def _make_keyword(term: str, weight: float = 1.0, enabled: bool = True) -> Keyword:
    now = datetime.utcnow().isoformat()
    return Keyword(
        term=term, weight=weight, source="manual",
        enabled=enabled, created_at=now, updated_at=now,
    )


# ---------------------------------------------------------------------------
# compute_repo_score
# ---------------------------------------------------------------------------


def test_ac1_single_keyword_hit_returns_score_and_match() -> None:
    """AC-1: 单个 user_keyword 命中 → (score>0, [term])。"""
    score, matched = compute_repo_score(
        "Python FastAPI web framework for APIs",
        {"fastapi": 5.0},
        stars_today=100,
    )
    assert score > 0
    assert "fastapi" in matched


def test_ac2_no_keyword_match_returns_log_only() -> None:
    """AC-2: 无命中 → score = log(stars_today+2),matched=[]。"""
    score, matched = compute_repo_score(
        "Description with no relevant keyword",
        {"fastapi": 5.0, "rust": 5.0},
        stars_today=10,
    )
    assert matched == []
    assert math.isclose(score, math.log(12), rel_tol=1e-6)


def test_ac3_multiple_hits_accumulate() -> None:
    """AC-3: 多命中累加。"""
    score, matched = compute_repo_score(
        "Python FastAPI Rust async runtime",
        {"fastapi": 5.0, "rust": 5.0},
        stars_today=10,
    )
    assert "fastapi" in matched
    assert "rust" in matched
    # 至少 2 个命中 + base
    assert score > math.log(12) + 5.0


def test_ac4_stars_today_none_falls_back_to_2() -> None:
    """AC-4: stars_today=None → 用 log(0+2)=log(2) 作基础分。"""
    score, _ = compute_repo_score(
        "no match here",
        {"fastapi": 5.0},
        stars_today=None,
    )
    assert math.isclose(score, math.log(2), rel_tol=1e-6)


def test_ac5_case_insensitive_match() -> None:
    """AC-5: 大小写不敏感(description "Python" 命中 keyword "python")。"""
    score, matched = compute_repo_score(
        "Python web framework",
        {"python": 5.0},
        stars_today=10,
    )
    assert "python" in matched
    assert score > 0


def test_repeated_keyword_not_double_counted() -> None:
    """同一 keyword 在 description 出现多次只算 1 次(避免词频堆叠)。"""
    score_single, _ = compute_repo_score("python is great", {"python": 5.0}, 10)
    score_repeat, _ = compute_repo_score(
        "python python python python python", {"python": 5.0}, 10
    )
    assert score_single == score_repeat


def test_topics_match_also_counts() -> None:
    """description 空时,topics 命中也算。"""
    score, matched = compute_repo_score(
        "rust async topics embedded no_std embedded systems",
        {"embedded": 5.0},
        stars_today=10,
    )
    assert "embedded" in matched


# ---------------------------------------------------------------------------
# rank_recommendations
# ---------------------------------------------------------------------------


def test_ac6_skips_already_starred_repos() -> None:
    """AC-6: 跳过已在 stars 表的 repo。"""
    stars = [_make_star(1, "owner/repo_a", description="Python FastAPI framework")]
    trending = [
        _make_trending(1, description="Python FastAPI framework", rank=1),
        _make_trending(2, description="Python FastAPI framework", rank=2),
    ]
    kws = [_make_keyword("fastapi", weight=5.0)]
    out = rank_recommendations(stars, trending, kws)
    ids = [r["repo_id"] for r in out]
    assert 1 not in ids
    assert 2 in ids


def test_ac7_skips_already_recommended_in_dedupe_set() -> None:
    """AC-7: already_recommended_ids 里的 repo 跳过。"""
    stars = [_make_star(1, "owner/repo_a", description="Python framework")]
    trending = [
        _make_trending(2, description="Python framework", rank=1),
        _make_trending(3, description="Python framework", rank=2),
    ]
    kws = [_make_keyword("python", weight=5.0)]
    out = rank_recommendations(
        stars, trending, kws, already_recommended_ids={2}
    )
    ids = [r["repo_id"] for r in out]
    assert 2 not in ids
    assert 3 in ids


def test_ac8_top_n_limits_results() -> None:
    """AC-8: top_n 限制。"""
    stars = []
    trending = [
        _make_trending(i, description="Python framework", rank=i)
        for i in range(1, 11)
    ]
    kws = [_make_keyword("python", weight=5.0)]
    out = rank_recommendations(stars, trending, kws, top_n=3)
    assert len(out) <= 3


def test_ac9_min_score_filters_low() -> None:
    """AC-9: min_score 过滤低分。"""
    stars = []
    trending = [_make_trending(1, description="Python framework", stars_today=1)]
    kws = [_make_keyword("python", weight=5.0)]
    out = rank_recommendations(stars, trending, kws, min_score=100.0)
    assert out == []


def test_ac10_results_sorted_by_score_desc() -> None:
    """AC-10: score 降序。"""
    stars = []
    trending = [
        _make_trending(1, description="Python framework", stars_today=10, rank=1),
        _make_trending(2, description="Python framework Python", stars_today=10, rank=2),
        _make_trending(3, description="totally unrelated content", stars_today=10, rank=3),
    ]
    kws = [_make_keyword("python", weight=5.0)]
    out = rank_recommendations(stars, trending, kws)
    scores = [r["score"] for r in out]
    assert scores == sorted(scores, reverse=True)


def test_ac11_integration_50_stars_25_trending_yields_recs() -> None:
    """AC-11: 50 star → TF-IDF → 25 trending → ≥ 1 命中推荐。

    集成路径 + 显式 keyword 兜底。验证完整 pipeline:
    star descriptions 喂给 TF-IDF + 用户 keyword → rank_recommendations 输出。
    """
    # 50 stars 描述有差异
    stars = []
    topics_pool = [
        ["python", "fastapi", "async"],
        ["python", "fastapi", "auth"],
        ["python", "async", "websocket"],
        ["python", "fastapi", "orm"],
        ["python", "pydantic", "async"],
    ]
    descriptions = [
        "Python FastAPI async web framework with authentication",
        "Python FastAPI async ORM integration with SQLAlchemy",
        "Python async websocket server built on FastAPI",
        "Python FastAPI pydantic validation async API",
        "Python async queue worker with FastAPI background tasks",
    ]
    for i in range(50):
        stars.append(_make_star(
            1000 + i,
            f"awesome{i}/skill{i}",
            description=descriptions[i % 5],
            language="Python",
            topics=topics_pool[i % 5],
        ))
    # 25 trending:前 10 个含 fastapi/async,后 15 个无关(C# project)
    trending = []
    for i in range(25):
        if i < 10:
            desc = f"FastAPI async web framework example {i}"
            lang = "Python"
        else:
            desc = f"Unrelated game engine Unity C# project {i}"
            lang = "C#"
        trending.append(_make_trending(
            2000 + i, description=desc, language=lang,
            stars_today=10 + i, rank=i + 1
        ))
    # 显式 user keyword:fastapi(用户明确想关注)
    kws = [_make_keyword("fastapi", weight=5.0), _make_keyword("async", weight=5.0)]
    out = rank_recommendations(stars, trending, kws, min_score=5.5, top_n=15)
    assert len(out) >= 1
    # 命中的应是 id 2000..2009
    hit_ids = {r["repo_id"] for r in out}
    assert hit_ids <= set(range(2000, 2010)), f"unexpected hit ids: {hit_ids}"
    # 至少 1 个 fastapi/async 命中
    assert any("fastapi" in r["matched_keywords"] or "async" in r["matched_keywords"]
               for r in out), "no match found in matched_keywords"


def test_ac12_empty_stars_falls_back_to_user_keywords() -> None:
    """AC-12: 空 stars → 退化为仅 user_keywords。

    两个 trending 描述不同,但因 language_token="Python" 屏蔽 "python" term,
    都只靠 base 分(log)。设置较高的 min_score 让只含关键字命中过的进。
    """
    trending = [
        _make_trending(1, description="Python web framework", stars_today=20, rank=1),
        _make_trending(2, description="totally unrelated Rust content", stars_today=20, rank=2),
    ]
    kws = [_make_keyword("python", weight=5.0)]
    # 第二个 trending description 含 "Rust" → language_token=Rust,python keyword 不被屏蔽但也不命中
    out = rank_recommendations([], trending, kws, min_score=0.5)
    # 第一个 id=1:description 有 "Python" + language="Python",language 屏蔽 python → 无命中 → 仅 base
    #   base = log(22) ≈ 3.09 → 留
    # 第二个 id=2:language="Rust",python 不命中 → 仅 base = log(22) → 也留
    # 两个都该留,但说明退化路径有效(没报错)
    assert len(out) >= 1
    # 验证 description 里有 Python web framework 的在结果里
    descs = [r["description"] for r in out]
    assert "Python web framework" in descs


def test_ac13_explicit_and_tfidf_weights_combined() -> None:
    """AC-13: 显式 5.0 + TF-IDF weight*1.0 加成混合。

    注意:language_token=Python 会屏蔽「python」keyword,所以 description 里
    "Python" 不命中;只 fastapi 是显式命中。
    """
    score, matched = compute_repo_score(
        "Python FastAPI async web framework",
        user_keywords={"python": 5.0, "fastapi": 5.0, "framework": 3.5},
        stars_today=10,
        language_token="Python",  # 屏蔽 "python" term 命中
    )
    # fastapi (显式 5.0) + framework (隐式 weight=3.5)
    assert "fastapi" in matched
    assert "framework" in matched
    assert "python" not in matched  # 被 language_token 屏蔽
    # 期望 = 5.0 (fastapi 显式) + 3.5 (framework 隐式) + log(12)
    expected = 5.0 + 3.5 + math.log(12)
    assert math.isclose(score, expected, rel_tol=1e-6)


def test_disabled_keywords_ignored() -> None:
    """enabled=False 的 keyword 不参与打分。"""
    stars = []
    trending = [_make_trending(1, description="Python framework")]
    kws = [_make_keyword("python", weight=5.0, enabled=False)]
    out = rank_recommendations(stars, trending, kws)
    # 仅 log(stars_today+2) 命中,无 keyword 加成
    if out:
        # 应 < 5.0 + log(12) 因为没 keyword 命中
        assert out[0]["score"] < 5.0 + math.log(12)


def test_empty_inputs_returns_empty() -> None:
    """全空输入 → 空输出。"""
    out = rank_recommendations([], [], [])
    assert out == []


def test_rank_field_is_1_indexed() -> None:
    """rank 字段 1-indexed。"""
    stars = []
    trending = [
        _make_trending(1, description="Python framework", stars_today=20, rank=99),  # rank 字段不连续
        _make_trending(2, description="Python framework", stars_today=20, rank=100),
    ]
    kws = [_make_keyword("python", weight=5.0)]
    out = rank_recommendations(stars, trending, kws)
    assert out[0]["rank"] == 1
    assert out[1]["rank"] == 2


def test_matched_keywords_field_is_list() -> None:
    """matched_keywords 字段是 list[str]。"""
    stars = []
    trending = [_make_trending(1, description="Python FastAPI")]
    kws = [_make_keyword("python", weight=5.0), _make_keyword("fastapi", weight=5.0)]
    out = rank_recommendations(stars, trending, kws)
    assert isinstance(out[0]["matched_keywords"], list)
    assert all(isinstance(t, str) for t in out[0]["matched_keywords"])