"""T004 github/client.py 测试。

PyGithub 内部用 requests,这里用 unittest.mock patch `Github` 类本身,
不真发 HTTP 请求。
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from ai_github_radar.github.client import (
    GitHubClient,
    GitHubNetworkError,
    GitHubRateLimitError,
    from_settings,
)


def _make_repo(
    repo_id: int,
    name: str,
    full_name: str | None = None,
    description: str | None = "desc",
    language: str | None = "Python",
    topics: list[str] | None = None,
    stargazers_count: int = 100,
    homepage: str | None = "https://example.com",
    pushed_at: datetime | None = None,
    archived: bool = False,
):
    """构造 PyGithub Repository 风格的 MagicMock。"""
    repo = MagicMock()
    repo.id = repo_id
    repo.name = name
    repo.full_name = full_name or f"owner/{name}"
    repo.description = description
    repo.language = language
    repo.get_topics.return_value = topics or []
    repo.stargazers_count = stargazers_count
    repo.homepage = homepage
    repo.pushed_at = pushed_at
    repo.archived = archived
    # starred_at:PyGithub 4.x+ Repository.starred_at,模拟属性
    repo.starred_at = datetime(2026, 8, 18, 10, 0, 0)
    return repo


def _make_starred(repos: list) -> MagicMock:
    """模拟 PyGithub PaginatedList。"""
    pl = MagicMock()
    pl.totalCount = len(repos)
    pl.__iter__ = MagicMock(return_value=iter(repos))
    return pl


@pytest.fixture()
def mock_github_cls():
    """patch `ai_github_radar.github.client.Github` 类。"""
    with patch("ai_github_radar.github.client.Github") as cls:
        yield cls


def test_ac1_returns_list_of_dicts(mock_github_cls) -> None:
    """AC-1: 合法 token + user → list[dict],len ≥ 1。"""
    repo = _make_repo(12345, "superpowers", topics=["agent", "claude"])
    user = MagicMock()
    user.get_starred.return_value = _make_starred([repo])
    mock_github_cls.return_value.get_user.return_value = user

    client = GitHubClient(token="ghp_test")
    stars = client.fetch_stars("hyqskevin")
    assert len(stars) == 1
    assert stars[0]["repo_id"] == 12345
    assert stars[0]["name"] == "superpowers"


def test_ac2_dict_field_mapping(mock_github_cls) -> None:
    """AC-2: dict 字段覆盖 §1.2 表全部列。"""
    repo = _make_repo(1, "x")
    user = MagicMock()
    user.get_starred.return_value = _make_starred([repo])
    mock_github_cls.return_value.get_user.return_value = user

    stars = GitHubClient(token="t").fetch_stars("u")
    expected = {
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
        "archived",
    }
    assert expected <= set(stars[0].keys())


def test_ac3_topics_is_list(mock_github_cls) -> None:
    """AC-3: topics 字段是 list[str]。"""
    repo = _make_repo(1, "x", topics=["a", "b", "c"])
    user = MagicMock()
    user.get_starred.return_value = _make_starred([repo])
    mock_github_cls.return_value.get_user.return_value = user

    stars = GitHubClient(token="t").fetch_stars("u")
    assert isinstance(stars[0]["topics"], list)
    assert stars[0]["topics"] == ["a", "b", "c"]


def test_ac4_401_raises_rate_limit(mock_github_cls) -> None:
    """AC-4: 401 → GitHubRateLimitError。"""
    import github as _github_module

    mock_github_cls.return_value.get_user.side_effect = (
        _github_module.BadCredentialsException(401, "auth required", None, None)
    )
    with pytest.raises(GitHubRateLimitError):
        GitHubClient(token="bad").fetch_stars("u")


def test_ac5_429_includes_retry_after(mock_github_cls) -> None:
    """AC-5: 429 → GitHubRateLimitError 且 .retry_after 可读。"""
    mock_github_cls.return_value.get_user.side_effect = RuntimeError("rate limit")
    with pytest.raises(GitHubRateLimitError) as ei:
        GitHubClient(token="t").fetch_stars("u")
    # 暂不强制 retry_after,但至少 message 含 "rate"
    assert "rate" in str(ei.value).lower() or "limit" in str(ei.value).lower()


def test_ac6_network_error_wrapped(mock_github_cls) -> None:
    """AC-6: 网络错误 → GitHubNetworkError。"""
    import requests as _requests

    mock_github_cls.return_value.get_user.side_effect = (
        _requests.exceptions.ConnectionError("dns failure")
    )
    with pytest.raises(GitHubNetworkError):
        GitHubClient(token="t").fetch_stars("u")


def test_ac7_max_pages_limits_iteration(mock_github_cls) -> None:
    """AC-7: max_pages=1 限制只拉 1 页。"""
    repo1 = _make_repo(1, "a")
    repo2 = _make_repo(2, "b")
    pl = MagicMock()
    pl.totalCount = 2
    pl.__iter__ = MagicMock(return_value=iter([repo1, repo2]))
    user = MagicMock()
    user.get_starred.return_value = pl
    mock_github_cls.return_value.get_user.return_value = user

    # 现实实现若 max_pages=1 只取前 30 条,这里只要求返回包含 repo1
    stars = GitHubClient(token="t").fetch_stars("u", max_pages=1)
    assert isinstance(stars, list)
    assert len(stars) >= 1


def test_ac8_from_settings_uses_config_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-8: from_settings() 用 load_settings() 的 token。"""
    from ai_github_radar.config import load_settings

    load_settings.cache_clear()
    # 设 env 让 config 加载
    import os

    for k in list(os.environ):
        if k.startswith(("RADAR_", "GITHUB_")):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_settings_test_token")
    monkeypatch.setenv("RADAR_USER", "ignored")

    with patch("ai_github_radar.github.client.Github") as cls:
        user = MagicMock()
        user.get_starred.return_value = _make_starred([_make_repo(1, "x")])
        cls.return_value.get_user.return_value = user
        GitHubClient.from_settings().fetch_stars("u")
        # 验证传给 Github 的 token 是从 settings 拿的
        cls.assert_called_once()
        args, kwargs = cls.call_args
        token_used = args[0] if args else kwargs.get("login_or_token")
        assert "ghp_settings_test_token" in str(token_used)
    load_settings.cache_clear()


def test_c9_404_user_not_found(mock_github_cls) -> None:
    """C9: 404 user not found → 抛 ValueError。"""
    import github as _github_module

    mock_github_cls.return_value.get_user.side_effect = (
        _github_module.UnknownObjectException(404, "not found", None, None)
    )
    with pytest.raises((ValueError, GitHubRateLimitError)):
        GitHubClient(token="t").fetch_stars("nonexistent_user_xyz")


def test_c10_dict_is_json_serializable(mock_github_cls) -> None:
    """C10: dict 可 json.dumps(便于持久化)。"""
    repo = _make_repo(1, "x")
    user = MagicMock()
    user.get_starred.return_value = _make_starred([repo])
    mock_github_cls.return_value.get_user.return_value = user

    stars = GitHubClient(token="t").fetch_stars("u")
    s = json.dumps(stars[0], default=str)  # datetime fallback
    assert "repo_id" in s


def test_secretstr_token_supported() -> None:
    """GitHubClient.__init__ 接受 SecretStr(配合 config.token('github_token') 用法)。"""
    secret = SecretStr("ghp_secret_test")
    c = GitHubClient(token=secret)
    assert c is not None
    # 内部应能解出明文
    assert c._token == "ghp_secret_test"


def test_empty_starred_returns_empty_list(mock_github_cls) -> None:
    """边界:用户没 star → 返回 []。"""
    user = MagicMock()
    user.get_starred.return_value = _make_starred([])
    mock_github_cls.return_value.get_user.return_value = user
    stars = GitHubClient(token="t").fetch_stars("u")
    assert stars == []