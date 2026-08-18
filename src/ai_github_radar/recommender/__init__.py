"""recommender 子包 — T008 pipeline.py 匹配打分."""

from ai_github_radar.recommender.pipeline import (  # noqa: F401
    compute_repo_score,
    rank_recommendations,
)

__all__ = ["compute_repo_score", "rank_recommendations"]