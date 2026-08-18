"""GitHub trending + search 抓取 — T005.

两条互补抓取路径:
- fetch_trending_html(language, since):拉 https://github.com/trending 解析 HTML
- search_repositories(keywords, min_stars, ...):调 GitHub search API

路径协调(T012 scan 命令编排,trending.py 自身不做)。
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Callable, Optional

import httpx
from bs4 import BeautifulSoup

from ai_github_radar.github.client import GitHubRateLimitError

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

UA = "ai-github-radar/0.1 (+https://github.com/hyqskevin/ai-github-radar)"
GITHUB_TRENDING_URL = "https://github.com/trending"
GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"

DEFAULT_TIMEOUT = 15.0
MAX_RETRIES = 3
BACKOFF_BASE = 1.0  # 指数退避基数(秒),实际睡眠 1s, 2s, 4s


class TrendingFetchError(Exception):
    """HTML 解析失败 / 拉取失败标志(供 T012 fallback 编排用)。"""


# ---------------------------------------------------------------------------
# fetch_trending_html
# ---------------------------------------------------------------------------


def fetch_trending_html(
    language: Optional[str] = None,
    since: str = "daily",
    *,
    client: Optional[httpx.Client] = None,
) -> list[dict]:
    """拉 GitHub trending HTML 解析为 list[dict]。

    dict 字段:
      repo_id:int (HTML 无 id,占位 0)
      full_name:str
      description:str|None
      language:str|None
      stars_today:int|None
      rank:int
      fetched_at:str (ISO)
    """
    if since not in {"daily", "weekly", "monthly"}:
        raise ValueError(f"since must be daily|weekly|monthly, got {since!r}")

    # URL 构造:/trending[/<lang>][?<since>]
    path_parts = [GITHUB_TRENDING_URL]
    if language:
        path_parts.append(language.lower())
    url = "/".join(path_parts)
    if since != "daily":
        url += f"?since={since}"

    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=DEFAULT_TIMEOUT, headers={"User-Agent": UA})

    try:
        if own_client:
            try:
                resp = client.get(url)
            finally:
                client.close()
        else:
            resp = client.get(url)
        resp.raise_for_status()
        return _parse_trending_html(resp.text)
    except httpx.HTTPError as e:
        raise TrendingFetchError(f"trending fetch HTTP error: {e}") from e
    except Exception as e:  # bs4 parse 失败 / 网络层 / 其他
        raise TrendingFetchError(f"trending parse failed: {e}") from e


def _parse_trending_html(html: str) -> list[dict]:
    """bs4 解析 trending HTML。

    GitHub 2024-2026 真实结构(简化):
      <article class="Box-row">
        <h2><a href="/owner/name">owner / name</a></h2>
        <p>description</p>
        <span itemprop="programmingLanguage">Python</span>
        <span>123 stars today</span>
      </article>
    """
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.find_all("article")
    if not articles:
        raise TrendingFetchError("no <article> tags found in HTML")

    out: list[dict] = []
    fetched_at = datetime.now(timezone.utc).isoformat()
    for rank, art in enumerate(articles, start=1):
        # full_name
        link = art.find("h2")
        if not link or not link.find("a"):
            continue
        href = link.find("a").get("href", "")
        # href like "/owner/name" or "/owner/name" → "owner/name"
        full_name = href.strip("/")
        if not full_name or "/" not in full_name:
            continue

        # description
        desc_tag = art.find("p")
        description = desc_tag.get_text(strip=True) if desc_tag else None

        # language
        lang_tag = art.find("span", attrs={"itemprop": "programmingLanguage"})
        language = lang_tag.get_text(strip=True) if lang_tag else None

        # stars_today — 找含 "stars today" 的文本
        stars_today = None
        for span in art.find_all("span"):
            txt = span.get_text()
            if "stars today" in txt:
                m = re.search(r"([\d,]+)", txt.replace(",", ""))
                if m:
                    try:
                        stars_today = int(m.group(1))
                    except ValueError:
                        pass
                break

        out.append({
            "repo_id": 0,  # HTML 无 id,占位
            "full_name": full_name,
            "description": description,
            "language": language,
            "stars_today": stars_today,
            "rank": rank,
            "fetched_at": fetched_at,
        })
    if not out:
        raise TrendingFetchError("no repos parsed from HTML")
    return out


# ---------------------------------------------------------------------------
# search_repositories
# ---------------------------------------------------------------------------


def search_repositories(
    keywords: list[str],
    *,
    min_stars: int = 0,
    language: Optional[str] = None,
    sort: str = "stars",
    order: str = "desc",
    per_page: int = 30,
    client: Optional[httpx.Client] = None,
    token: Optional[str] = None,
    _retry_sleep: Callable[[float], None] = time.sleep,
) -> list[dict]:
    """用 GitHub search API 按关键词 + 阈值检索 repo。

    keywords: 至少 1 个,OR 连接。
    min_stars: 0 表示不限。
    language: 限定语言,None 表示不限。
    """
    if not keywords:
        raise ValueError("keywords must be non-empty list")
    if not all(isinstance(k, str) and k.strip() for k in keywords):
        raise ValueError("keywords must be non-empty strings")
    if sort not in {"stars", "updated", "forks"}:
        raise ValueError(f"sort must be stars|updated|forks, got {sort!r}")
    if order not in {"desc", "asc"}:
        raise ValueError(f"order must be desc|asc, got {order!r}")
    if not (1 <= per_page <= 100):
        raise ValueError(f"per_page must be 1..100, got {per_page}")

    # 构造 q
    keyword_expr = " OR ".join(k.strip() for k in keywords)
    q_parts = [f"{{{keyword_expr}}}"]
    if language:
        q_parts.append(f"language:{language.lower()}")
    if min_stars > 0:
        q_parts.append(f"stars:>={min_stars}")
    q = " ".join(q_parts)

    params = {
        "q": q,
        "sort": sort,
        "order": order,
        "per_page": per_page,
    }
    headers = {
        "User-Agent": UA,
        "Accept": "application/vnd.github+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=DEFAULT_TIMEOUT, headers=headers)

    try:
        return _search_with_retry(client, params, sleep_fn=_retry_sleep)
    finally:
        if own_client:
            client.close()


def _search_with_retry(
    client: httpx.Client,
    params: dict,
    *,
    sleep_fn: Callable[[float], None],
) -> list[dict]:
    """带指数退避的 search API 调用。"""
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.get(GITHUB_SEARCH_URL, params=params)
            if resp.status_code == 401:
                raise GitHubRateLimitError(f"search 401 unauthorized: {resp.text}")
            if resp.status_code == 403:
                # 403 也可能是限流(secondary rate limit)
                raise GitHubRateLimitError(f"search 403 forbidden: {resp.text[:200]}")
            if resp.status_code == 429:
                # 退避重试
                sleep_fn(BACKOFF_BASE * (2 ** attempt))
                continue
            resp.raise_for_status()
            return _parse_search_response(resp.json())
        except GitHubRateLimitError:
            raise
        except httpx.HTTPError as e:
            last_err = e
            sleep_fn(BACKOFF_BASE * (2 ** attempt))
            continue
    # 3 次都 429
    raise GitHubRateLimitError(
        f"search API 429 after {MAX_RETRIES} retries; last_err={last_err}"
    )


def _parse_search_response(payload: dict) -> list[dict]:
    """search API items[] → list[dict] 对齐 fetch_trending_html 字段。"""
    items = payload.get("items", [])
    out: list[dict] = []
    fetched_at = datetime.now(timezone.utc).isoformat()
    for rank, repo in enumerate(items, start=1):
        out.append({
            "repo_id": repo.get("id", 0),
            "full_name": repo.get("full_name", ""),
            "description": repo.get("description"),
            "language": repo.get("language"),
            "stars_today": repo.get("stargazers_count"),  # search API 无 stars_today,用总量
            "rank": rank,
            "fetched_at": fetched_at,
        })
    return out