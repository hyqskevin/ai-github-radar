"""keywords 子包 — T006 TF-IDF 提取 + Keyword CRUD.

T007 LLM 升级路径在此基础上挂载。
"""

from ai_github_radar.keywords.extractor import extract_keywords_tf_idf  # noqa: F401
from ai_github_radar.keywords.repository import KeywordRepository  # noqa: F401

__all__ = ["extract_keywords_tf_idf", "KeywordRepository"]