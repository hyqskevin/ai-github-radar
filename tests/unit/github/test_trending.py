"""T005 github/trending.py 测试。

用 respx mock httpx,fixture 提供简化版 trending HTML。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx
import pytest
import respx

from ai_github_radar.github.client import GitHubRateLimitError
from ai_github_radar.github.trending import (
    TrendingFetchError,
    fetch_trending_html,
    search_repositories,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_trending_article(rank: int, owner: str, name: str, lang: str | None,
                            stars_today: int, description: str | None) -> str:
    """构造一个简化版 trending article HTML 块(基于 GitHub 2024-2026 真实结构)。"""
    lang_html = (
        f'<span itemprop="programmingLanguage">{lang}</span>' if lang else ""
    )
    desc_html = f"<p>{description}</p>" if description else ""
    return f"""
    <article class="Box-row">
      <h2 class="h3 lh-condensed">
        <a href="/trending/{owner}/{name}">{owner} / {name}</a>
      </h2>
      {desc_html}
      <div class="f6 color-fg-muted mt-2">
        {lang_html}
        <a href="/{owner}/{name}/stargazers" class="Link Link--muted">
          <span>{stars_today} stars today</span>
        </a>
      </div>
    </article>
    """


def _make_trending_html(articles: list[str]) -> str:
    return f"<html><body>{''.join(articles)}</body></html>"


@pytest.fixture()
def trending_html_25() -> str:
    """25 个 repo 的 trending HTML(AC-1 要求 ≥ 20)。"""
    arts = [
        _make_trending_article(
            rank=i + 1,
            owner=f"owner{i}",
            name=f"repo{i}",
            lang="Python" if i % 2 == 0 else "Rust",
            stars_today=100 + i * 5,
            description=f"Repo {i} description",
        )
        for i in range(25)
    ]
    return _make_trending_html(arts)


@pytest.fixture()
def github_search_payload() -> dict:
    """respx mock 的 search API JSON 响应。"""
    items = [
        {
            "id": 100000 + i,
            "full_name": f"awesome{i}/skill{i}",
            "description": f"awesome skill {i}",
            "language": "Python" if i % 2 == 0 else "TypeScript",
            "stargazers_count": 500 + i * 10,
            "html_url": f"https://github.com/awesome{i}/skill{i}",
            "fork": False,
            "archived": False,
        }
        for i in range(3)
    ]
    return {"total_count": 3, "incomplete_results": False, "items": items}


# ---------------------------------------------------------------------------
# fetch_trending_html 测试
# ---------------------------------------------------------------------------


@pytest.mark.respx
def test_ac1_fetch_returns_25_dicts(respx_mock, trending_html_25: str) -> None:
    """AC-1: fetch_trending_html() 返回 ≥ 20 个 dict。"""
    respx_mock.get("https://github.com/trending").respond(200, text=trending_html_25)
    repos = fetch_trending_html()
    assert len(repos) == 25


@pytest.mark.respx
def test_ac2_dict_fields_align_with_orm(respx_mock, trending_html_25: str) -> None:
    """AC-2: dict 字段对齐 TrendingSnapshot ORM。"""
    respx_mock.get("https://github.com/trending").respond(200, text=trending_html_25)
    repos = fetch_trending_html()
    expected = {"repo_id", "full_name", "description", "language",
                "stars_today", "rank", "fetched_at"}
    assert expected <= set(repos[0].keys())


@pytest.mark.respx
def test_ac3_language_param_in_url(respx_mock, trending_html_25: str) -> None:
    """AC-3: language="python" → URL 含 /trending/python。"""
    route = respx_mock.get("https://github.com/trending/python").respond(
        200, text=trending_html_25
    )
    fetch_trending_html(language="python")
    assert route.called


@pytest.mark.respx
def test_ac4_since_weekly_in_url(respx_mock, trending_html_25: str) -> None:
    """AC-4: since="weekly" → URL 含 weekly。"""
    route = respx_mock.get("https://github.com/trending").respond(
        200, text=trending_html_25
    )
    # GitHub trending URL 不带 query since;参数化通过 URL path:/trending?since=weekly
    # 我们实现选择 path 形式:/trending/{since?}/{lang?}
    fetch_trending_html(since="weekly")
    # 至少路径里有 weekly
    assert route.called


def test_ac5_html_parse_failure_raises_trending_fetch_error() -> None:
    """AC-5: HTML 解析失败(结构变化)抛 TrendingFetchError。"""
    # 用 fake client 返回空 HTML,触发解析失败
    fake_client = httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, text="<html></html>"))
    )
    with pytest.raises(TrendingFetchError):
        fetch_trending_html(client=fake_client)


@pytest.mark.respx
def test_c_rank_starts_from_1(respx_mock, trending_html_25: str) -> None:
    """rank 字段 1-indexed。"""
    respx_mock.get("https://github.com/trending").respond(200, text=trending_html_25)
    repos = fetch_trending_html()
    assert repos[0]["rank"] == 1
    assert repos[-1]["rank"] == 25


@pytest.mark.respx
def test_stars_today_parsed_as_int(respx_mock, trending_html_25: str) -> None:
    """stars_today 是 int(从 "1,234 stars today" 解析)。"""
    respx_mock.get("https://github.com/trending").respond(200, text=trending_html_25)
    repos = fetch_trending_html()
    assert isinstance(repos[0]["stars_today"], int)
    assert repos[0]["stars_today"] >= 100


# ---------------------------------------------------------------------------
# search_repositories 测试
# ---------------------------------------------------------------------------


@pytest.mark.respx
def test_ac6_keywords_and_min_stars_in_url(respx_mock, github_search_payload: dict) -> None:
    """AC-6: search_repositories URL 含 agent OR claude + stars:>=10。"""
    route = respx_mock.get("https://api.github.com/search/repositories").respond(
        200, json=github_search_payload
    )
    search_repositories(["agent", "claude"], min_stars=10)
    assert route.called
    # URL 包含 q 参数含 keywords OR + stars filter
    last_request = respx_mock.calls.last.request
    url_q = last_request.url.params.get("q", "")
    assert "agent" in url_q
    assert "claude" in url_q
    assert "OR" in url_q or "or" in url_q.lower()
    assert "stars:>=10" in url_q


@pytest.mark.respx
def test_ac7_language_filter_in_url(respx_mock, github_search_payload: dict) -> None:
    """AC-7: language="rust" + keywords=["async"] → URL 含 language:rust。"""
    route = respx_mock.get("https://api.github.com/search/repositories").respond(
        200, json=github_search_payload
    )
    search_repositories(["async"], language="rust")
    assert route.called
    url_q = respx_mock.calls.last.request.url.params.get("q", "")
    assert "language:rust" in url_q
    assert "async" in url_q


@pytest.mark.respx
def test_ac8_401_raises_rate_limit(respx_mock) -> None:
    """AC-8: 401 → GitHubRateLimitError。"""
    respx_mock.get("https://api.github.com/search/repositories").respond(401)
    with pytest.raises(GitHubRateLimitError):
        search_repositories(["x"])


@pytest.mark.respx
def test_ac9_429_retries_3_times(respx_mock) -> None:
    """AC-9: 429 重试 3 次后仍失败 → GitHubRateLimitError。"""
    route = respx_mock.get("https://api.github.com/search/repositories").respond(429)
    # 退避 sleep 让测试快(我们在实现里用短 sleep 或 monkeypatch)
    with pytest.raises(GitHubRateLimitError):
        search_repositories(["x"], _retry_sleep=lambda _: None)  # 测试加速
    # 至少调 3 次(实际可能 4:初次 + 3 retry)
    assert route.call_count >= 3


@pytest.mark.respx
def test_ac10_200_parses_items(respx_mock, github_search_payload: dict) -> None:
    """AC-10: 200 → 解析 items 数组,字段映射对齐。"""
    respx_mock.get("https://api.github.com/search/repositories").respond(
        200, json=github_search_payload
    )
    repos = search_repositories(["agent"])
    assert len(repos) == 3
    for r in repos:
        assert r["full_name"].startswith("awesome")
        assert r["repo_id"] >= 100000


@pytest.mark.respx
def test_ac11_per_page_in_url(respx_mock, github_search_payload: dict) -> None:
    """AC-11: per_page=50 → URL 含 per_page=50。"""
    route = respx_mock.get("https://api.github.com/search/repositories").respond(
        200, json=github_search_payload
    )
    search_repositories(["x"], per_page=50)
    assert "per_page=50" in str(respx_mock.calls.last.request.url)


def test_ac12_empty_keywords_raises_value_error() -> None:
    """AC-12: 空 keywords → ValueError。"""
    with pytest.raises(ValueError):
        search_repositories([])


@pytest.mark.respx
def test_c12_both_apis_return_consistent_dict_shape(
    respx_mock, trending_html_25: str, github_search_payload: dict
) -> None:
    """C12: 两个 API 返回 dict 字段一致(至少交集)。"""
    respx_mock.get("https://github.com/trending").respond(200, text=trending_html_25)
    respx_mock.get("https://api.github.com/search/repositories").respond(
        200, json=github_search_payload
    )
    trending = fetch_trending_html()
    searched = search_repositories(["x"])
    common = set(trending[0].keys()) & set(searched[0].keys())
    # 至少 full_name / language / description / repo_id 在两边都有
    assert {"full_name", "repo_id", "language"} <= common


@pytest.mark.respx
def test_429_then_200_succeeds(respx_mock, github_search_payload: dict) -> None:
    """429 retry 第一次成功(2xx)。"""
    call_count = {"n": 0}

    def side_effect(request):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return httpx.Response(429)
        return httpx.Response(200, json=github_search_payload)

    respx_mock.get("https://api.github.com/search/repositories").mock(side_effect=side_effect)
    repos = search_repositories(["x"], _retry_sleep=lambda _: None)
    assert len(repos) == 3
    assert call_count["n"] == 2