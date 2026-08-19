"""TF-IDF 关键字提取 — T006.

基于 sklearn.feature_extraction.text.TfidfVectorizer。
输入是 list[str](每个 star 的描述 + topics + language 拼成的文本),
输出 list[(term, weight)] 按 weight 降序。
"""

from __future__ import annotations

import re
from typing import Optional

from sklearn.feature_extraction.text import TfidfVectorizer

# 默认英文停用词 + GitHub 噪音
_DEFAULT_STOP_WORDS = frozenset(
    {
        "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "will", "would", "should", "could", "may", "might", "must",
        "i", "you", "he", "she", "it", "we", "they", "them", "this",
        "that", "these", "those", "for", "to", "of", "in", "on", "at",
        "by", "with", "as", "from", "into", "about", "between",
        "use", "using", "used", "based", "via", "new", "simple",
        "support", "supports", "supported",
    }
)


_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)


def _preprocess(text: str) -> str:
    """小写 + 去 emoji + 去 markdown 链接括号。"""
    if not text:
        return ""
    t = text.lower()
    t = _EMOJI_RE.sub(" ", t)
    # 去 markdown 图片语法 ![alt](url)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)
    # 去 markdown 链接 [text](url) → text
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    # 去多余空白
    t = re.sub(r"\s+", " ", t).strip()
    return t


def extract_keywords_tf_idf(
    docs: list[str],
    *,
    top_n: int = 50,
    min_df: int = 2,
    max_df: float = 0.95,
    ngram_range: tuple[int, int] = (1, 2),
    stop_words: Optional[set[str]] = None,
) -> list[tuple[str, float]]:
    """TF-IDF 提取关键字。

    Args:
        docs: 每个文档 1 个 str(star 描述+topics+language 拼接)
        top_n: 返回前 N 个关键字
        min_df: 最小文档频率(过滤噪声)
        max_df: 最大文档频率(过滤"出现太多"的词,如 'library')
        ngram_range: (1,1) 仅 unigram;(1,2) 含 bigram
        stop_words: 自定义停用词集合,与默认停用词合并

    Returns:
        [(term, weight), ...] 按 weight 降序,weight 是该 term 的平均 TF-IDF
    """
    if not docs:
        return []

    if top_n < 1:
        raise ValueError(f"top_n must be >= 1, got {top_n}")
    if min_df < 1:
        raise ValueError(f"min_df must be >= 1, got {min_df}")

    cleaned = [_preprocess(d) for d in docs]
    # 全部空字符串会让 TfidfVectorizer 报错,提前处理
    if all(not c for c in cleaned):
        return []

    combined_stops = _DEFAULT_STOP_WORDS | (stop_words or set())

    vectorizer = TfidfVectorizer(
        ngram_range=ngram_range,
        min_df=min_df,
        max_df=max_df,
        stop_words=list(combined_stops),
        token_pattern=r"(?u)\b[A-Za-z][A-Za-z0-9\-_]+\b",
    )
    try:
        matrix = vectorizer.fit_transform(cleaned)
    except ValueError:
        # 词汇表为空(全过滤掉了)→ 返回空
        return []

    feature_names = vectorizer.get_feature_names_out()
    if len(feature_names) == 0:
        return []

    # 每 term 的平均 TF-IDF(跨文档)
    mean_tfidf = matrix.mean(axis=0).A1  # shape: (n_features,)

    # 全部排好序再切片(确保稳定:weight 相同按 term 字典序)
    pairs = sorted(
        zip(feature_names, mean_tfidf),
        key=lambda x: (-x[1], x[0]),
    )
    out: list[tuple[str, float]] = [
        (term, float(w)) for term, w in pairs[:top_n]
    ]
    return out