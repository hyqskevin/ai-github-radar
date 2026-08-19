"""keywords 子包 — T006 TF-IDF + Keyword CRUD, T007 LLM 升级."""

from ai_github_radar.keywords.extractor import extract_keywords_tf_idf  # noqa: F401
from ai_github_radar.keywords.llm_upgrade import (  # noqa: F401
    LLMProvider,
    LLMProviderError,
    PROVIDERS,
    detect_provider,
    extract_keywords_via_llm,
)
from ai_github_radar.keywords.repository import KeywordRepository  # noqa: F401

__all__ = [
    "LLMProvider",
    "LLMProviderError",
    "KeywordRepository",
    "PROVIDERS",
    "detect_provider",
    "extract_keywords_tf_idf",
    "extract_keywords_via_llm",
]