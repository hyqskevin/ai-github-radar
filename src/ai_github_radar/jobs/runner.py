"""jobs/runner.py — 后台任务 runner (T129).

策略:ThreadPoolExecutor 跑 init / scan,记录到 jobs 表。
FastAPI BackgroundTasks 进程内 async 启动,服务关掉 job 就没了;
这是阶段二简版,阶段三可用 Redis/Celery。
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable

from sqlalchemy.orm import Session

from ai_github_radar.services.jobs import finish_job, start_job

log = logging.getLogger(__name__)

# 全局 executor(单实例,跨请求共用)
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="radar-job")


def submit_task(
    name: str,
    s: Session,
    fn: Callable[..., Any],
    **kwargs: Any,
) -> tuple[Future, int]:
    """提交后台任务。

    立刻创建 Job 记录(running),然后异步执行 fn。
    返回 (future, job_id) —前端可轮询 job_id 看 status。
    """
    from ai_github_radar.db.models import Job as JobModel
    job = start_job(s, name=name, payload=kwargs if kwargs else None)
    s.commit()  # 必须 commit,否则新 session 查不到
    job_id = job.id

    def _runner() -> None:
        from ai_github_radar.storage.db import session_scope
        log.info("job %d %s started with kwargs=%s", job_id, name, kwargs)
        try:
            result = fn(**kwargs)
            log.info("job %d %s success, marking done", job_id, name)
        except Exception as e:  # noqa: BLE001
            log.exception("job %d %s failed: %s", job_id, name, e)
            result = None
            error_msg = f"{type(e).__name__}: {e}"
        else:
            error_msg = None
        # 写结果(独立 try/finally 保证 db 一定更新)
        try:
            with session_scope() as ns:
                job = ns.get(JobModel, job_id)
                if job is not None:
                    finish_job(ns, job, result=result if isinstance(result, dict) else None, error=error_msg)
            log.info("job %d %s db updated", job_id, name)
        except Exception as db_err:  # noqa: BLE001
            log.exception("job %d %s DB write failed: %s", job_id, name, db_err)

    future = _executor.submit(_runner)
    return future, job_id


# 任务列表(给前端 /api/jobs/types 用)
TASK_TYPES = ["init", "scan"]


# ---------------------------------------------------------------------------
# 实际任务函数
# ---------------------------------------------------------------------------


def run_init(user: str, no_llm: bool = False) -> dict:
    """跑 init(用 CLI 的逻辑,但不 click)。

    优先级:
    1. 显式传的 user 参数
    2. SQLite settings 表的 github.user (T125:前端 /api/settings/all 持久化)
    3. .env 的 RADAR_USER
    """
    from ai_github_radar.github.client import GitHubClient
    from ai_github_radar.keywords import (
        detect_provider,
        extract_keywords_tf_idf,
        extract_keywords_via_llm,
    )
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.storage.repositories import (
        KeywordRepository,
        StarRepository,
    )
    from ai_github_radar.config import get_settings
    from ai_github_radar.services.settings import (
        KEY_GITHUB_TOKEN,
        KEY_GITHUB_USER,
        get_setting,
    )
    from ai_github_radar.cli.init_cmd import star_to_doc_dict

    init_db()  # 确保 settings 表存在

    # 1. 先看 SQLite settings 表(用户在 /init 页面存的配置)
    with session_scope() as s:
        db_user = get_setting(s, KEY_GITHUB_USER, "") or ""
        db_token = get_setting(s, KEY_GITHUB_TOKEN, "") or ""

    # 2. fallback 到 .env(T012 CLI 兼容)
    name = user or db_user
    token = db_token
    if not name or not token:
        try:
            settings = get_settings()
            name = name or settings.radar_user
            token = token or (
                settings.github_token.get_secret_value()
                if settings.github_token else None
            )
        except Exception:  # noqa: BLE001
            # .env 缺失时跳过,user/token 必须显式给
            pass
    if not name:
        raise ValueError("user required (set github.user in /init page or RADAR_USER in .env)")
    if not token:
        raise ValueError(
            "github token required — 在 /init 页面填 GitHub PAT,或在 .env 设 GITHUB_TOKEN"
        )

    gh = GitHubClient(token=token)
    star_dicts = gh.fetch_stars(name)

    with session_scope() as s:
        star_repo = StarRepository(s)
        n_stars = star_repo.upsert_many(star_dicts)
        docs = [star_to_doc_dict(d) for d in star_dicts]
        provider = None if no_llm else detect_provider()
        if provider is None:
            kw_results = extract_keywords_tf_idf(docs, top_n=50, min_df=2)
            source = "auto"
            kw_method = "TF-IDF"
        else:
            kw_results = extract_keywords_via_llm(docs, provider=provider, max_keywords=50)
            source = "auto"
            kw_method = f"LLM ({provider.value})"
        kw_repo = KeywordRepository(s)
        n_kws = kw_repo.bulk_upsert_from_tfidf(kw_results, source=source)

    return {
        "user": name,
        "stars": n_stars,
        "keywords": n_kws,
        "kw_method": kw_method,
    }


def run_scan(top: int = 10, language: str | None = None, since: str = "daily") -> dict:
    """跑 scan(走 cli/scan_cmd.do_scan,无 push)。"""
    from ai_github_radar.cli.scan_cmd import do_scan

    recs = do_scan(
        push_target="local",
        top=top,
        language=language,
        since=since,
        min_score=0.0,
        echo=lambda msg: log.info("scan: %s", msg),
    )
    if recs is None:
        raise RuntimeError("scan failed (trending fetch error)")
    return {
        "candidates": len(recs),
        "recommendations": len(recs),
        "top": top,
        "language": language or "all",
        "since": since,
    }