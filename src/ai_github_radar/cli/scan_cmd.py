"""radar scan 命令 — 拉 trending + 匹配 + 推送。"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import click

log = logging.getLogger(__name__)


@click.command("scan")
@click.option(
    "--push",
    "push_target",
    default="local",
    type=click.Choice(["local", "feishu", "email", "stdout", "json"]),
    help="推送目标",
)
@click.option("--top", default=10, show_default=True, help="最多推送几条")
@click.option("--language", default=None, help="trending 语言过滤(默认 all)")
@click.option("--since", default="daily", type=click.Choice(["daily", "weekly", "monthly"]))
@click.option("--min-score", default=0.0, type=float, help="过滤低分推荐")
def scan_cmd(
    push_target: str, top: int, language: str | None, since: str, min_score: float
) -> None:
    """扫描 trending + 匹配关键字 + 推送。"""
    from ai_github_radar.config import get_settings
    from ai_github_radar.github import trending as t_module
    from ai_github_radar.push import (
        push_email,
        push_feishu,
        render_json,
        write_recommendations,
    )
    from ai_github_radar.recommender.pipeline import rank_recommendations
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.storage.repositories import (
        KeywordRepository,
        RecommendationRepository,
        StarRepository,
        TrendingSnapshotRepository,
    )

    settings = get_settings()
    init_db()

    # 1. 拉 trending
    click.echo(f"→ fetching trending ({since}, lang={language or 'all'})...")
    try:
        trending_dicts = t_module.fetch_trending_html(language=language, since=since)
    except Exception as e:
        click.echo(f"✗ trending fetch failed: {e}", err=True)
        raise click.Abort()

    if not trending_dicts:
        click.echo("✗ no trending repos found")
        return

    # 2. DB: stars + keywords + dedupe set
    snapshot_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with session_scope() as s:
        # 写 trending 快照
        TrendingSnapshotRepository(s).upsert_many([
            {
                "repo_id": r["repo_id"],
                "snapshot_date": snapshot_date,
                "rank": r["rank"],
                "stars_today": r.get("stars_today"),
                "language": r.get("language"),
                "description": r.get("description"),
            }
            for r in trending_dicts
            if r.get("repo_id")
        ])
        stars = StarRepository(s).list_all()
        kws = KeywordRepository(s).list(enabled_only=True)
        dedupe_ids = RecommendationRepository(s).recent_repo_ids(days=7)

    # 3. 匹配
    click.echo(
        f"→ ranking {len(trending_dicts)} candidates "
        f"against {len(stars)} stars, {len(kws)} keywords..."
    )
    # 转为 TrendingSnapshot-like(用 SimpleNamespace 模拟 ORM 字段)
    from types import SimpleNamespace
    trending_objs = [
        SimpleNamespace(
            repo_id=r["repo_id"],
            rank=r["rank"],
            stars_today=r.get("stars_today"),
            language=r.get("language"),
            description=r.get("description"),
            snapshot_date=snapshot_date,
            fetched_at=r.get("fetched_at", snapshot_date),
        )
        for r in trending_dicts
        if r.get("repo_id")
    ]
    recs = rank_recommendations(
        stars, trending_objs, kws,
        already_recommended_ids=dedupe_ids,
        top_n=top, min_score=min_score,
    )
    click.echo(f"→ {len(recs)} recommendations")

    # 4. 推送
    if push_target == "stdout":
        click.echo(render_json(recs))
    elif push_target == "json":
        click.echo(render_json(recs))
    elif push_target == "local":
        p = write_recommendations(recs)
        click.echo(f"✓ wrote {p}")
    elif push_target == "feishu":
        if not settings.feishu_webhook_url:
            click.echo("✗ FEISHU_WEBHOOK_URL not set", err=True)
            raise click.Abort()
        try:
            push_feishu(recs, webhook_url=str(settings.feishu_webhook_url))
            click.echo(f"✓ pushed to feishu ({len(recs)} items)")
        except Exception as e:
            click.echo(f"✗ feishu push failed: {e}", err=True)
            raise click.Abort()
    elif push_target == "email":
        if not all([settings.smtp_host, settings.smtp_to]):
            click.echo("✗ SMTP_HOST / SMTP_TO not set", err=True)
            raise click.Abort()
        try:
            push_email(
                recs,
                smtp_host=settings.smtp_host,
                smtp_port=settings.smtp_port or 587,
                smtp_user=settings.smtp_user,
                smtp_password=(
                    settings.smtp_password.get_secret_value()
                    if settings.smtp_password else None
                ),
                smtp_to=settings.smtp_to,
            )
            click.echo(f"✓ emailed ({len(recs)} items)")
        except Exception as e:
            click.echo(f"✗ email push failed: {e}", err=True)
            raise click.Abort()

    # 5. 记录推送(用于 N-day dedupe)
    with session_scope() as s:
        rr = RecommendationRepository(s)
        for r in recs:
            rr.record_push(
                repo_id=r["repo_id"],
                score=r["score"],
                matched_keywords=r.get("matched_keywords") or [],
                channel=push_target,
            )