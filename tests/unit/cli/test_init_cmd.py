"""cli/init_cmd 测试 — 拉 stars + 提关键字 + 入库。"""

from __future__ import annotations

import os
from unittest.mock import patch


def _setup_env(tmp_path, monkeypatch):
    cwd_orig = os.getcwd()
    os.chdir(str(tmp_path))
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    monkeypatch.setenv("RADAR_USER", "test-user")
    # 清空所有 LLM env,强制 TF-IDF
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY",
              "DASHSCOPE_API_KEY", "MOONSHOT_API_KEY", "ZHIPUAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    from ai_github_radar.storage.db import reset_for_testing, init_db
    from ai_github_radar.config import load_settings
    load_settings.cache_clear()
    reset_for_testing()
    init_db()
    return cwd_orig


def test_init_runs_and_extracts_via_tfidf(tmp_path, monkeypatch, capsys) -> None:
    """init --no-llm 走 TF-IDF,拉 stars + 提关键字。"""
    cwd_orig = _setup_env(tmp_path, monkeypatch)

    fake_stars = [
        {
            "repo_id": i,
            "owner": f"o{i}", "name": f"r{i}", "full_name": f"o{i}/r{i}",
            "description": (
                "Python FastAPI async web framework with auth "
                "and high performance" if i % 2 == 0
                else "Rust async runtime for systems programming"
            ),
            "language": "Python" if i % 2 == 0 else "Rust",
            "topics": "python,fastapi,async" if i % 2 == 0 else "rust,async",
            "stargazers_count": 100 + i,
            "fetched_at": "2026-08-19T00:00:00",
        }
        for i in range(20)
    ]
    from click.testing import CliRunner
    from ai_github_radar.cli import cli
    with patch(
        "ai_github_radar.cli.init_cmd.GitHubClient"
    ) as mock_gh:
        instance = mock_gh.return_value
        instance.fetch_stars.return_value = fake_stars
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--no-llm"])
    assert result.exit_code == 0, result.output
    assert "initialized" in result.output
    assert "TF-IDF" in result.output

    # 验证 DB 写入
    from ai_github_radar.storage.db import session_scope
    from ai_github_radar.storage.repositories import (
        KeywordRepository, StarRepository,
    )
    with session_scope() as s:
        stars = StarRepository(s).list_all()
        kws = KeywordRepository(s).list()
    assert len(stars) == 20
    assert len(kws) >= 1
    os.chdir(cwd_orig)


def test_init_with_llm_when_key_set(tmp_path, monkeypatch, capsys) -> None:
    """OPENAI_API_KEY 配了 → 走 LLM 路径(实际不调 mock LLM 失败也走通)。"""
    cwd_orig = _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    fake_stars = [
        {
            "repo_id": i,
            "owner": f"o{i}", "name": f"r{i}", "full_name": f"o{i}/r{i}",
            "description": f"Generic description {i}",
            "language": "Python", "topics": None,
            "stargazers_count": 10,
            "fetched_at": "2026-08-19T00:00:00",
        }
        for i in range(5)
    ]
    from click.testing import CliRunner
    from ai_github_radar.cli import cli
    with patch("ai_github_radar.cli.init_cmd.GitHubClient") as mock_gh:
        instance = mock_gh.return_value
        instance.fetch_stars.return_value = fake_stars
        # mock extract_keywords_via_llm 返回 0 条(模拟 LLM 报错后 fallback)
        with patch(
            "ai_github_radar.cli.init_cmd.extract_keywords_via_llm",
            return_value=[],
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    # LLM 路径走通
    assert "LLM" in result.output or "TF-IDF" in result.output
    os.chdir(cwd_orig)


def test_init_empty_stars_does_not_crash(tmp_path, monkeypatch) -> None:
    """init 拉 0 stars → 友好退出。"""
    cwd_orig = _setup_env(tmp_path, monkeypatch)

    from click.testing import CliRunner
    from ai_github_radar.cli import cli
    with patch("ai_github_radar.cli.init_cmd.GitHubClient") as mock_gh:
        instance = mock_gh.return_value
        instance.fetch_stars.return_value = []
        runner = CliRunner()
        result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    assert "no stars" in result.output.lower()
    os.chdir(cwd_orig)


def test_init_user_override(tmp_path, monkeypatch) -> None:
    """init --user NAME 覆盖 settings.radar_user。"""
    cwd_orig = _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("RADAR_USER", "settings-user")

    captured_user = {}

    class FakeGH:
        def __init__(self, token):
            self.token = token

        def fetch_stars(self, user):
            captured_user["user"] = user
            return []

    from click.testing import CliRunner
    from ai_github_radar.cli import cli
    with patch(
        "ai_github_radar.cli.init_cmd.GitHubClient",
        FakeGH,
    ):
        runner = CliRunner()
        runner.invoke(cli, ["init", "--user", "explicit-user"])
    assert captured_user["user"] == "explicit-user"
    os.chdir(cwd_orig)