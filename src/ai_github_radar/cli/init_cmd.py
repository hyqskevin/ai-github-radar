"""radar init 命令 — 拉 stars + 提关键字 + 入库。"""

from __future__ import annotations

import logging

import click

log = logging.getLogger(__name__)


@click.command("init")
@click.option("--user", default=None, help="GitHub username(默认从 config 读)")
@click.option("--no-llm", is_flag=True, help="强制走 TF-IDF,不用 LLM")
def init_cmd(user: str | None, no_llm: bool) -> None:
    """初始化:拉 stars + 关键字提取 + 持久化。"""
    from ai_github_radar.config import get_settings
    from ai_github_radar.github.client import GitHubClient
    from ai_github_radar.keywords import (
        detect_provider,
        extract_keywords_tf_idf,
        extract_keywords_via_llm,
    )
    from ai_github_radar.recommender.pipeline import _star_to_doc
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.storage.repositories import (
        KeywordRepository,
        StarRepository,
    )

    settings = get_settings()
    name = user or settings.radar_user
    init_db()
    click.echo(f"→ fetching stars for {name}...")
    gh = GitHubClient(token=settings.github_token.get_secret_value())
    star_dicts = gh.fetch_stars(name)
    if not star_dicts:
        click.echo("✗ no stars found (check token / username)")
        return

    with session_scope() as s:
        star_repo = StarRepository(s)
        n_stars = star_repo.upsert_many(star_dicts)
        # 提关键字
        docs = [_star_to_doc_dict(d) for d in star_dicts]
        provider = None if no_llm else detect_provider()
        if provider is None:
            kw_results = extract_keywords_tf_idf(docs, top_n=50, min_df=2)
            source = "auto"
            click.echo(f"→ extracted {len(kw_results)} keywords via TF-IDF")
        else:
            kw_results = extract_keywords_via_llm(
                docs, provider=provider, max_keywords=50
            )
            source = "auto"
            click.echo(f"→ extracted {len(kw_results)} keywords via LLM ({provider.value})")
        kw_repo = KeywordRepository(s)
        n_kws = kw_repo.bulk_upsert_from_tfidf(kw_results, source=source)

    click.echo(f"✓ initialized {n_stars} stars, {n_kws} keywords")


def _star_to_doc_dict(d: dict) -> str:
    """Star dict → TF-IDF 输入文本(与 recommender._star_to_doc 一致)。"""
    parts = [d.get("description") or ""]
    topics = d.get("topics")
    if topics:
        if isinstance(topics, str):
            parts.extend(t.strip() for t in topics.split(",") if t.strip())
        elif isinstance(topics, list):
            parts.extend(str(t) for t in topics)
    lang = d.get("language")
    if lang:
        parts.append(lang)
    return " ".join(parts)