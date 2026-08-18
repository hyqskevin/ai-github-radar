"""cli/scan_cmd.do_scan 的 feishu/email 推送路径覆盖。"""

from __future__ import annotations

import os
from datetime import datetime
from unittest.mock import MagicMock, patch


def _setup(tmp_path, monkeypatch):
    cwd_orig = os.getcwd()
    os.chdir(str(tmp_path))
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    monkeypatch.setenv("RADAR_USER", "test-user")
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY",
              "DASHSCOPE_API_KEY", "MOONSHOT_API_KEY", "ZHIPUAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    from ai_github_radar.storage.db import reset_for_testing, init_db
    from ai_github_radar.config import load_settings
    load_settings.cache_clear()
    reset_for_testing()
    init_db()
    return cwd_orig


def _seed(s):
    from ai_github_radar.db.models import Keyword
    s.add(Keyword(
        term="fastapi", weight=5.0, source="manual", enabled=True,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
    ))
    s.commit()


def test_do_scan_feishu_push_calls_api(tmp_path, monkeypatch) -> None:
    """do_scan(push='feishu') → push_feishu。"""
    cwd_orig = _setup(tmp_path, monkeypatch)
    from pydantic import HttpUrl
    monkeypatch.setenv("FEISHU_WEBHOOK_URL", "https://open.feishu.cn/open-apis/bot/v2/hook/abc")

    from ai_github_radar.storage.db import session_scope
    with session_scope() as s:
        _seed(s)

    fake_trending = [
        {
            "repo_id": 8001, "rank": 1, "stars_today": 100,
            "language": "Python", "description": "fastapi example",
            "fetched_at": "2026-08-19T00:00:00",
        },
    ]
    with patch(
        "ai_github_radar.github.trending.fetch_trending_html",
        return_value=fake_trending,
    ), patch(
        "ai_github_radar.cli.scan_cmd.push_feishu",
    ) as mock_push:
        from ai_github_radar.cli.scan_cmd import do_scan
        recs = do_scan(push_target="feishu")
    assert recs is not None
    assert mock_push.called
    os.chdir(cwd_orig)


def test_do_scan_feishu_without_weburl_returns_none(tmp_path, monkeypatch) -> None:
    """do_scan(push='feishu') 但无 webhook URL → 返 None。"""
    cwd_orig = _setup(tmp_path, monkeypatch)
    # 不设 FEISHU_WEBHOOK_URL
    from ai_github_radar.storage.db import session_scope
    with session_scope() as s:
        _seed(s)

    fake_trending = [
        {
            "repo_id": 8002, "rank": 1, "stars_today": 100,
            "language": "Python", "description": "fastapi example",
            "fetched_at": "2026-08-19T00:00:00",
        },
    ]
    with patch(
        "ai_github_radar.github.trending.fetch_trending_html",
        return_value=fake_trending,
    ):
        from ai_github_radar.cli.scan_cmd import do_scan
        recs = do_scan(push_target="feishu")
    assert recs is None
    os.chdir(cwd_orig)


def test_do_scan_email_push_calls_api(tmp_path, monkeypatch) -> None:
    """do_scan(push='email') → push_email。"""
    cwd_orig = _setup(tmp_path, monkeypatch)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("SMTP_TO", "alice@example.com")

    from ai_github_radar.storage.db import session_scope
    with session_scope() as s:
        _seed(s)

    fake_trending = [
        {
            "repo_id": 8003, "rank": 1, "stars_today": 100,
            "language": "Python", "description": "fastapi example",
            "fetched_at": "2026-08-19T00:00:00",
        },
    ]
    with patch(
        "ai_github_radar.github.trending.fetch_trending_html",
        return_value=fake_trending,
    ), patch(
        "ai_github_radar.cli.scan_cmd.push_email",
        return_value={"to": ["alice@example.com"], "subject": "x", "sent_at": "now"},
    ) as mock_push:
        from ai_github_radar.cli.scan_cmd import do_scan
        recs = do_scan(push_target="email")
    assert recs is not None
    assert mock_push.called
    os.chdir(cwd_orig)


def test_do_scan_email_without_config_returns_none(tmp_path, monkeypatch) -> None:
    """do_scan(push='email') 但 smtp 未配 → 返 None。"""
    cwd_orig = _setup(tmp_path, monkeypatch)
    # 不设 smtp
    from ai_github_radar.storage.db import session_scope
    with session_scope() as s:
        _seed(s)

    fake_trending = [
        {
            "repo_id": 8004, "rank": 1, "stars_today": 100,
            "language": "Python", "description": "fastapi example",
            "fetched_at": "2026-08-19T00:00:00",
        },
    ]
    with patch(
        "ai_github_radar.github.trending.fetch_trending_html",
        return_value=fake_trending,
    ):
        from ai_github_radar.cli.scan_cmd import do_scan
        recs = do_scan(push_target="email")
    assert recs is None
    os.chdir(cwd_orig)


def test_do_scan_feishu_push_failure_returns_none(tmp_path, monkeypatch) -> None:
    """do_scan(push='feishu') 推送抛错 → 返 None。"""
    cwd_orig = _setup(tmp_path, monkeypatch)
    monkeypatch.setenv("FEISHU_WEBHOOK_URL", "https://open.feishu.cn/open-apis/bot/v2/hook/abc")

    from ai_github_radar.storage.db import session_scope
    with session_scope() as s:
        _seed(s)

    fake_trending = [
        {
            "repo_id": 8005, "rank": 1, "stars_today": 100,
            "language": "Python", "description": "fastapi example",
            "fetched_at": "2026-08-19T00:00:00",
        },
    ]
    with patch(
        "ai_github_radar.github.trending.fetch_trending_html",
        return_value=fake_trending,
    ), patch(
        "ai_github_radar.cli.scan_cmd.push_feishu",
        side_effect=RuntimeError("webhook down"),
    ):
        from ai_github_radar.cli.scan_cmd import do_scan
        recs = do_scan(push_target="feishu")
    assert recs is None
    os.chdir(cwd_orig)


def test_do_scan_email_push_failure_returns_none(tmp_path, monkeypatch) -> None:
    """do_scan(push='email') 推送抛错 → 返 None。"""
    cwd_orig = _setup(tmp_path, monkeypatch)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_TO", "alice@example.com")

    from ai_github_radar.storage.db import session_scope
    with session_scope() as s:
        _seed(s)

    fake_trending = [
        {
            "repo_id": 8006, "rank": 1, "stars_today": 100,
            "language": "Python", "description": "fastapi example",
            "fetched_at": "2026-08-19T00:00:00",
        },
    ]
    with patch(
        "ai_github_radar.github.trending.fetch_trending_html",
        return_value=fake_trending,
    ), patch(
        "ai_github_radar.cli.scan_cmd.push_email",
        side_effect=RuntimeError("smtp down"),
    ):
        from ai_github_radar.cli.scan_cmd import do_scan
        recs = do_scan(push_target="email")
    assert recs is None
    os.chdir(cwd_orig)


def test_do_scan_records_push_channel_feishu(tmp_path, monkeypatch) -> None:
    """feishu 推送成功后记录 channel='feishu'。"""
    cwd_orig = _setup(tmp_path, monkeypatch)
    monkeypatch.setenv("FEISHU_WEBHOOK_URL", "https://open.feishu.cn/open-apis/bot/v2/hook/abc")

    from ai_github_radar.storage.db import session_scope
    from ai_github_radar.storage.repositories import RecommendationRepository
    with session_scope() as s:
        _seed(s)

    fake_trending = [
        {
            "repo_id": 8007, "rank": 1, "stars_today": 100,
            "language": "Python", "description": "fastapi example",
            "fetched_at": "2026-08-19T00:00:00",
        },
    ]
    with patch(
        "ai_github_radar.github.trending.fetch_trending_html",
        return_value=fake_trending,
    ), patch(
        "ai_github_radar.cli.scan_cmd.push_feishu",
        return_value={"StatusCode": 0, "msg": "ok"},
    ):
        from ai_github_radar.cli.scan_cmd import do_scan
        do_scan(push_target="feishu")

    with session_scope() as s:
        from sqlalchemy import select
        from ai_github_radar.db.models import Recommendation
        rows = s.execute(select(Recommendation)).scalars().all()
    assert any(r.channel == "feishu" and r.repo_id == 8007 for r in rows)
    os.chdir(cwd_orig)