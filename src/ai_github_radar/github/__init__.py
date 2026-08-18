"""github 子包 — T004 GitHub API 封装。

阶段一仅做 stars 拉取,trending T005。
"""

from ai_github_radar.github.client import (  # noqa: F401
    GitHubClient,
    GitHubNetworkError,
    GitHubRateLimitError,
    from_settings,
)