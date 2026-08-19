"""GitHub API 客户端 — T004.

封装 PyGithub,提供:
- GitHubClient.fetch_stars(user):拉 /user/starred 全量,转 list[dict]
- from_settings():从 load_settings() 取 token 构造 client
- 错误类型:GitHubRateLimitError / GitHubNetworkError
"""

from __future__ import annotations

import logging
from typing import Optional, Union

import github as _github_module
import requests
from github import Github
from pydantic import SecretStr

log = logging.getLogger(__name__)


class GitHubRateLimitError(Exception):
    """401/403/429 等限流/认证错误。"""


class GitHubNetworkError(Exception):
    """网络层失败(超时 / DNS / connection refused / 等)。"""


class GitHubClient:
    """PyGithub 封装,供 init / scan 等命令使用。"""

    def __init__(self, token: Union[str, SecretStr]):
        # SecretStr 或 str 都接受,内部统一 str
        if isinstance(token, SecretStr):
            self._token: str = token.get_secret_value()
        else:
            self._token = str(token)
        self._gh = Github(self._token, per_page=100)

    @classmethod
    def from_settings(cls) -> "GitHubClient":
        """从 load_settings() 读 token 构造 client。"""
        from ai_github_radar.config import load_settings

        s = load_settings()
        return cls(token=s.token("github_token"))

    def fetch_stars(self, user: str, *, max_pages: Optional[int] = None) -> list[dict]:
        """拉 /users/{user}/starred 全量,每个 repo 转 dict(对应 Star ORM 字段)。

        max_pages: 仅用于测试,限制最多拉 N 页(每页 100 条,per_page 见 __init__)。
        """
        try:
            u = self._gh.get_user(user)
            starred = u.get_starred()
        except _github_module.BadCredentialsException as e:
            raise GitHubRateLimitError(f"GitHub auth failed: {e}") from e
        except _github_module.UnknownObjectException as e:
            raise ValueError(f"GitHub user not found: {user!r}") from e
        except requests.exceptions.RequestException as e:
            raise GitHubNetworkError(f"GitHub network error: {e}") from e
        except Exception as e:  # PyGithub RateLimitExceeded 等
            msg = str(e).lower()
            if "rate" in msg or "limit" in msg or "abuse" in msg:
                raise GitHubRateLimitError(f"GitHub rate limit: {e}") from e
            if "connection" in msg or "timeout" in msg or "resolve" in msg:
                raise GitHubNetworkError(f"GitHub network: {e}") from e
            raise

        out: list[dict] = []
        for i, repo in enumerate(starred):
            if max_pages is not None and i >= max_pages * 100:
                break
            out.append(self._repo_to_dict(repo))
        return out

    @staticmethod
    def _repo_to_dict(repo) -> dict:
        """Repository → dict,字段对齐 Star ORM。"""
        # owner
        try:
            owner_login = repo.owner.login
        except Exception:
            owner_login = ""

        return {
            "repo_id": repo.id,
            "owner": owner_login,
            "name": repo.name,
            "full_name": repo.full_name,
            "description": repo.description,
            "language": repo.language,
            "topics": list(repo.get_topics() or []),
            "homepage": repo.homepage,
            "stargazers_count": repo.stargazers_count,
            "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else None,
            "starred_at": repo.starred_at.isoformat() if getattr(repo, "starred_at", None) else None,
            "archived": bool(repo.archived),
        }


def from_settings() -> GitHubClient:
    """工厂函数(API 友好),内部转调 GitHubClient.from_settings()。"""
    return GitHubClient.from_settings()