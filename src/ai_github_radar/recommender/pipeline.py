"""推荐 pipeline — T008.

输入:
  - stars: list[Star](用户提供兴趣关键字来源)
  - trending: list[TrendingSnapshot](候选集)
  - keywords: list[Keyword](用户显式订阅,只取 enabled=True)

输出:
  - list[dict],字段:repo_id, full_name, description, language, score,
    matched_keywords (list[str]), rank, stars_today,按 score 降序
"""

from __future__ import annotations

import math
import re
from typing import Optional

from ai_github_radar.db.models import Keyword, Star, TrendingSnapshot
from ai_github_radar.keywords.extractor import extract_keywords_tf_idf

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# 显式 keyword 命中权重(用户配 keyword 时每命中一个 +5.0)
EXPLICIT_HIT_WEIGHT = 5.0

# TF-IDF keyword weight 阈值(weight < 此值不参与隐式命中,避免噪声)
IMPLICIT_HIT_MIN_WEIGHT = 3.0

# stars_today log 平滑基数
STARS_TODAY_LOG_BASE = 2.0

# TF-IDF 提取数量(从 stars 提多少关键字)
DEFAULT_TFIDF_TOP_N = 50

# 默认 top_n
DEFAULT_TOP_N = 10


# ---------------------------------------------------------------------------
# 文本处理
# ---------------------------------------------------------------------------


# 按非字母数字分隔,小写后筛掉空串
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-_]+")


def _tokenize(text: str) -> list[str]:
    """小写分词,保留 1+ 字母开头的 token(含 / - _ 等)。"""
    if not text:
        return []
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _topic_list(star: Star) -> list[str]:
    """从 Star.topics(逗号分隔字符串)取 topic 列表。"""
    if not star.topics:
        return []
    return [t.strip().lower() for t in star.topics.split(",") if t.strip()]


def _star_to_doc(star: Star) -> str:
    """Star → TF-IDF 输入文本(description + topics + language)。"""
    parts = [star.description or ""]
    parts.extend(_topic_list(star))
    if star.language:
        parts.append(star.language)
    return " ".join(parts)


def _trending_to_text(t: TrendingSnapshot) -> str:
    """TrendingSnapshot → 检索文本(description + language)。"""
    parts = [t.description or ""]
    if t.language:
        parts.append(t.language)
    return " ".join(parts)


def _trending_keywords(t: TrendingSnapshot) -> set[str]:
    """从 trending 描述 + language 提取 token 集合(用于关键字匹配)。"""
    return set(_tokenize(_trending_to_text(t)))


# ---------------------------------------------------------------------------
# 单 repo 打分
# ---------------------------------------------------------------------------


def compute_repo_score(
    repo_text: str,
    user_keywords: dict[str, float],
    stars_today: Optional[int],
    *,
    language_token: str | None = None,
) -> tuple[float, list[str]]:
    """单个 repo 的命中分数 + 命中关键字列表。

    算法:
      score = base + explicit_hit_count * EXPLICIT_HIT_WEIGHT
            + implicit_hit_count * (avg_tf_idf_weight) * 1.0
      base = log(stars_today + 2) if stars_today is not None else log(2)
      explicit hit = term in user_keywords 且 weight >= EXPLICIT_HIT_WEIGHT
      implicit hit = term in user_keywords 且 IMPLICIT_HIT_MIN_WEIGHT <= weight < EXPLICIT_HIT_WEIGHT

    language_token: trending.repo 的 language 字段值(如 "Python"),如果它恰好等
    于某个 keyword 的 term,**不算命中**(避免 language 这种通用信号污染打分)。
    """
    # base
    if stars_today is None:
        base = math.log(STARS_TODAY_LOG_BASE)
    else:
        base = math.log(stars_today + STARS_TODAY_LOG_BASE)

    tokens = set(_tokenize(repo_text))
    if not tokens:
        return base, []

    matched_terms: list[str] = []
    explicit_count = 0
    implicit_weight_sum = 0.0

    for term, weight in user_keywords.items():
        # language token 屏蔽:无论 weight 多少,若 keyword term == language 都不命中
        if language_token and term == language_token.lower():
            continue
        # term 必须出现在 tokens 中(精确小写匹配)
        # term 可能是 bigram("machine learning")需要空格包含匹配
        if " " in term:
            # 多词 term:文本里直接 substr 匹配
            haystack = " " + " ".join(tokens) + " "
            if (" " + term + " ") in haystack:
                matched_terms.append(term)
                if weight >= EXPLICIT_HIT_WEIGHT:
                    explicit_count += 1
                elif weight >= IMPLICIT_HIT_MIN_WEIGHT:
                    implicit_weight_sum += weight
        else:
            if term in tokens:
                matched_terms.append(term)
                if weight >= EXPLICIT_HIT_WEIGHT:
                    explicit_count += 1
                elif weight >= IMPLICIT_HIT_MIN_WEIGHT:
                    implicit_weight_sum += weight

    score = base + explicit_count * EXPLICIT_HIT_WEIGHT + implicit_weight_sum * 1.0
    return score, matched_terms


# ---------------------------------------------------------------------------
# 主入口:rank_recommendations
# ---------------------------------------------------------------------------


def rank_recommendations(
    stars: list[Star],
    trending: list[TrendingSnapshot],
    keywords: list[Keyword],
    *,
    already_recommended_ids: Optional[set[int]] = None,
    top_n: int = DEFAULT_TOP_N,
    min_score: float = 0.0,
    tfidf_top_n: int = DEFAULT_TFIDF_TOP_N,
) -> list[dict]:
    """主入口。

    步骤:
      1. 从 stars 跑 TF-IDF 提取隐式关键字(若 stars 空则跳过)
      2. 合并 user_keywords(显式 weight=5.0) + tfidf_keywords(weight=TF-IDF*10)
      3. 对每个 trending repo:
         - 跳过已 star / 在 already_recommended_ids
         - compute_repo_score
      4. 按 score 降序,过滤 < min_score,取 top_n
      5. rank 字段重排 1-indexed
    """
    if not trending:
        return []

    # 1. TF-IDF 从 stars 提关键字
    tfidf_weighted: dict[str, float] = {}
    if stars:
        docs = [_star_to_doc(s) for s in stars]
        tfidf_results = extract_keywords_tf_idf(
            docs, top_n=tfidf_top_n, min_df=2, ngram_range=(1, 2)
        )
        # weight 已经在 extractor 里按平均 TF-IDF 排序;过滤太小的
        for term, w in tfidf_results:
            if w * 10.0 >= IMPLICIT_HIT_MIN_WEIGHT:
                tfidf_weighted[term] = min(w * 10.0, 10.0)

    # 2. 合并 user_keywords:显式 keyword(weight=5.0)优先,tfidf 补充
    user_keywords: dict[str, float] = {}
    for kw in keywords:
        if not kw.enabled:
            continue
        # 显式 keyword 的 weight 可能是用户改的(非 5.0),但 source=="manual" 即显式
        if kw.source == "manual":
            user_keywords[kw.term.lower()] = EXPLICIT_HIT_WEIGHT
        else:
            # source=="auto" 的 keyword weight 取原值
            user_keywords[kw.term.lower()] = kw.weight

    # 隐式 TF-IDF 关键字:不覆盖显式
    for term, w in tfidf_weighted.items():
        if term not in user_keywords:
            user_keywords[term] = w

    # 3. 已 star repo_id 集合 + 7-day dedupe 集合
    starred_ids = {s.repo_id for s in stars}
    rec_ids = already_recommended_ids or set()

    # 4. 对每个 trending 计算 score
    candidates: list[tuple[float, list[str], TrendingSnapshot]] = []
    for t in trending:
        if t.repo_id in starred_ids or t.repo_id in rec_ids:
            continue
        repo_text = _trending_to_text(t)
        score, matched = compute_repo_score(
            repo_text,
            user_keywords,
            t.stars_today,
            language_token=t.language,
        )
        if score < min_score:
            continue
        candidates.append((score, matched, t))

    # 5. 排序 + 切片
    candidates.sort(key=lambda x: (-x[0], x[2].repo_id))
    top = candidates[:top_n]

    # 6. 构造输出 dict
    out: list[dict] = []
    for rank, (score, matched, t) in enumerate(top, start=1):
        out.append({
            "repo_id": t.repo_id,
            "full_name": "",  # TrendingSnapshot ORM 无 full_name,推送时去 GitHub API 拉
            "description": t.description or "",
            "language": t.language,
            "score": round(score, 4),
            "matched_keywords": matched,
            "rank": rank,
            "stars_today": t.stars_today,
        })
    return out