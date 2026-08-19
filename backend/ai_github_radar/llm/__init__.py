"""llm 子包 — T130 LLM 仓库简介 + 关键字 rationale。"""
from ai_github_radar.llm.summarizer import (  # noqa: F401
    SummaryResult,
    available_models,
    explain_keyword,
    resolve_llm,
    summarize_repo,
)

__all__ = [
    "SummaryResult",
    "available_models",
    "explain_keyword",
    "resolve_llm",
    "summarize_repo",
]