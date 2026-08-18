"""cli/scan_cmd.do_scan 编排层覆盖测试。

mock trending fetch + DB,验证 do_scan 走通完整 scan 路径。
"""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest


@pytest.fixture()
def fake_env(tmp_path, monkeypatch):
    """隔离 cwd 到 tmp_path,设置 GITHUB_TOKEN 让 settings 能构造。"""
    cwd_orig = os.getcwd()
    os.chdir(str(tmp_path))
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_fake_token_for_unit_test")
    monkeypatch.setenv("RADAR_USER", "test-user")
    monkeypatch.setenv("OPENAI_API_KEY", "")  # 强制 TF-IDF
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "")
    monkeypatch.setenv("MOONSHOT_API_KEY", "")
    monkeypatch.setenv("ZHIPUAI_API_KEY", "")
    from ai_github_radar.storage.db import reset_for_testing, init_db
    from ai_github_radar.config import load_settings
    load_settings.cache_clear()
    reset_for_testing()
    init_db()
    yield tmp_path
    os.chdir(cwd_orig)


def _seed_stars_and_kws(s):
    from datetime import datetime
    from ai_github_radar.db.models import Star, Keyword
    s.add(Star(
        repo_id=1001, owner="o1", name="r1", full_name="o1/r1",
        description="Python FastAPI async web framework",
        language="Python", topics="python,fastapi,async",
        stargazers_count=100, fetched_at=datetime.utcnow().isoformat(),
    ))
    s.add(Keyword(
        term="fastapi", weight=5.0, source="manual", enabled=True,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
    ))
    s.commit()


def test_do_scan_local_writes_file(fake_env, capsys) -> None:
    """do_scan(push_target='local') 走 trending + 匹配 + 写文件。"""
    from ai_github_radar.cli.scan_cmd import do_scan
    from ai_github_radar.storage.db import session_scope
    from ai_github_radar.storage.repositories import StarRepository, KeywordRepository

    with session_scope() as s:
        _seed_stars_and_kws(s)

    fake_trending = [
        {
            "repo_id": 2001, "rank": 1, "stars_today": 100,
            "language": "Python", "description": "FastAPI async web framework example",
            "fetched_at": "2026-08-19T00:00:00",
        },
        {
            "repo_id": 2002, "rank": 2, "stars_today": 50,
            "language": "Rust", "description": "totally unrelated Rust game engine",
            "fetched_at": "2026-08-19T00:00:00",
        },
    ]
    with patch(
        "ai_github_radar.github.trending.fetch_trending_html",
        return_value=fake_trending,
    ):
        recs = do_scan(push_target="local", top=5)

    assert recs is not None
    assert len(recs) >= 1
    # 第一条是 id=2001(FastAPI 命中)
    assert recs[0]["repo_id"] == 2001
    assert "fastapi" in recs[0]["matched_keywords"]


def test_do_scan_stdout_does_not_write_file(fake_env) -> None:
    """do_scan(stdout=True) 不写文件。"""
    from ai_github_radar.cli.scan_cmd import do_scan
    from ai_github_radar.storage.db import session_scope

    with session_scope() as s:
        _seed_stars_and_kws(s)

    fake_trending = [
        {
            "repo_id": 3001, "rank": 1, "stars_today": 100,
            "language": "Python", "description": "fastapi example",
            "fetched_at": "2026-08-19T00:00:00",
        },
    ]
    with patch(
        "ai_github_radar.github.trending.fetch_trending_html",
        return_value=fake_trending,
    ):
        recs = do_scan(push_target="local", stdout=True)

    # stdout=True 不会写 .md/.json 文件
    out_dir = fake_env / "data" / "recommendations"
    if out_dir.exists():
        # 应只有 .json 或 .md,但 stdout 时不写
        assert not any(out_dir.iterdir()), "stdout mode should not write files"


def test_do_scan_trending_fetch_failure_returns_none(fake_env) -> None:
    """trending 抓取失败 → do_scan 返 None。"""
    from ai_github_radar.cli.scan_cmd import do_scan
    from ai_github_radar.storage.db import session_scope

    with session_scope() as s:
        _seed_stars_and_kws(s)

    with patch(
        "ai_github_radar.github.trending.fetch_trending_html",
        side_effect=RuntimeError("network down"),
    ):
        recs = do_scan(push_target="local")

    assert recs is None


def test_do_scan_empty_trending_returns_empty_list(fake_env) -> None:
    """空 trending → 返 []。"""
    from ai_github_radar.cli.scan_cmd import do_scan
    from ai_github_radar.storage.db import session_scope

    with session_scope() as s:
        _seed_stars_and_kws(s)

    with patch(
        "ai_github_radar.github.trending.fetch_trending_html",
        return_value=[],
    ):
        recs = do_scan(push_target="stdout", stdout=True)
    assert recs == []


def test_do_scan_records_push_to_db(fake_env) -> None:
    """do_scan 推送后写 Recommendation 行(dedupe 用)。"""
    from ai_github_radar.cli.scan_cmd import do_scan
    from ai_github_radar.storage.db import session_scope
    from ai_github_radar.storage.repositories import RecommendationRepository

    with session_scope() as s:
        _seed_stars_and_kws(s)

    fake_trending = [
        {
            "repo_id": 4001, "rank": 1, "stars_today": 100,
            "language": "Python", "description": "fastapi example",
            "fetched_at": "2026-08-19T00:00:00",
        },
    ]
    with patch(
        "ai_github_radar.github.trending.fetch_trending_html",
        return_value=fake_trending,
    ):
        do_scan(push_target="stdout", stdout=True)

    with session_scope() as s:
        ids = RecommendationRepository(s).recent_repo_ids(days=7)
    assert 4001 in ids


def test_do_scan_uses_7day_dedupe(fake_env) -> None:
    """已推荐过的 repo_id 不再返。"""
    from datetime import datetime, timedelta
    from ai_github_radar.cli.scan_cmd import do_scan
    from ai_github_radar.storage.db import session_scope
    from ai_github_radar.storage.repositories import RecommendationRepository

    with session_scope() as s:
        _seed_stars_and_kws(s)
        # 预先 record 5001 → 7 天内会被过滤
        RecommendationRepository(s).record_push(
            repo_id=5001, score=99.0, matched_keywords=["fastapi"],
            channel="local", pushed_at=datetime.utcnow().isoformat(),
        )

    fake_trending = [
        {
            "repo_id": 5001, "rank": 1, "stars_today": 100,
            "language": "Python", "description": "fastapi example",
            "fetched_at": "2026-08-19T00:00:00",
        },
        {
            "repo_id": 5002, "rank": 2, "stars_today": 50,
            "language": "Python", "description": "fastapi other example",
            "fetched_at": "2026-08-19T00:00:00",
        },
    ]
    with patch(
        "ai_github_radar.github.trending.fetch_trending_html",
        return_value=fake_trending,
    ):
        recs = do_scan(push_target="stdout", stdout=True)
    assert recs is not None
    ids = [r["repo_id"] for r in recs]
    assert 5001 not in ids
    assert 5002 in ids


def test_do_scan_old_dedupe_expires(fake_env) -> None:
    """8 天前推荐的会被重新推(过期)。"""
    from datetime import datetime, timedelta
    from ai_github_radar.cli.scan_cmd import do_scan
    from ai_github_radar.storage.db import session_scope
    from ai_github_radar.storage.repositories import RecommendationRepository

    with session_scope() as s:
        _seed_stars_and_kws(s)
        # 8 天前推送
        old_time = (datetime.utcnow() - timedelta(days=8)).isoformat()
        RecommendationRepository(s).record_push(
            repo_id=6001, score=99.0, matched_keywords=["fastapi"],
            channel="local", pushed_at=old_time,
        )

    fake_trending = [
        {
            "repo_id": 6001, "rank": 1, "stars_today": 100,
            "language": "Python", "description": "fastapi example",
            "fetched_at": "2026-08-19T00:00:00",
        },
    ]
    with patch(
        "ai_github_radar.github.trending.fetch_trending_html",
        return_value=fake_trending,
    ):
        recs = do_scan(push_target="stdout", stdout=True)
    ids = [r["repo_id"] for r in (recs or [])]
    assert 6001 in ids  # 已过期,重新推荐


def test_do_scan_skips_already_starred(fake_env) -> None:
    """已 star 的 repo 不出现在推荐。"""
    from ai_github_radar.cli.scan_cmd import do_scan
    from ai_github_radar.storage.db import session_scope

    with session_scope() as s:
        _seed_stars_and_kws(s)

    fake_trending = [
        {
            "repo_id": 1001, "rank": 1, "stars_today": 100,
            "language": "Python", "description": "fastapi example",
            "fetched_at": "2026-08-19T00:00:00",
        },  # 1001 在 stars 里
        {
            "repo_id": 7002, "rank": 2, "stars_today": 50,
            "language": "Python", "description": "fastapi other",
            "fetched_at": "2026-08-19T00:00:00",
        },
    ]
    with patch(
        "ai_github_radar.github.trending.fetch_trending_html",
        return_value=fake_trending,
    ):
        recs = do_scan(push_target="stdout", stdout=True)
    ids = [r["repo_id"] for r in (recs or [])]
    assert 1001 not in ids
    assert 7002 in ids