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
TASK_TYPES = ["init", "fetch_stars", "extract_keywords", "scan"]


# ---------------------------------------------------------------------------
# 实际任务函数
# ---------------------------------------------------------------------------


def _resolve_github_user_token(user: str) -> tuple[str, str]:
    """共享:从 db settings / .env 取 user + token。"""
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.config import get_settings
    from ai_github_radar.services.settings import (
        KEY_GITHUB_TOKEN,
        KEY_GITHUB_USER,
        get_setting,
    )

    init_db()
    with session_scope() as s:
        db_user = get_setting(s, KEY_GITHUB_USER, "") or ""
        db_token = get_setting(s, KEY_GITHUB_TOKEN, "") or ""

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
            pass
    if not name:
        raise ValueError("user required (set github.user in /init page or RADAR_USER in .env)")
    if not token:
        raise ValueError(
            "github token required — 在 /init 页面填 GitHub PAT,或在 .env 设 GITHUB_TOKEN"
        )
    return name, token


def run_fetch_stars(user: str = "") -> dict:
    """T144: 仅拉 GitHub stars 写到 stars 表,不提取关键字。

    返回: {"user": str, "stars": int}
    """
    from ai_github_radar.github.client import GitHubClient
    from ai_github_radar.storage.db import session_scope
    from ai_github_radar.storage.repositories import StarRepository

    name, token = _resolve_github_user_token(user)

    gh = GitHubClient(token=token)
    star_dicts = gh.fetch_stars(name)

    with session_scope() as s:
        star_repo = StarRepository(s)
        n_stars = star_repo.upsert_many(star_dicts)

    return {"user": name, "stars": n_stars}


def run_extract_keywords(no_llm: bool = False) -> dict:
    """T144: 仅从已有 stars 提取关键字写 keywords 表,不调用 GitHub。

    返回: {"keywords": int, "kw_method": str}
    """
    from ai_github_radar.keywords import (
        detect_provider,
        extract_keywords_tf_idf,
        extract_keywords_via_llm,
    )
    from ai_github_radar.storage.db import session_scope
    from ai_github_radar.storage.repositories import (
        KeywordRepository,
        StarRepository,
    )
    from ai_github_radar.cli.init_cmd import star_to_doc_dict

    with session_scope() as s:
        star_repo = StarRepository(s)
        stars = star_repo.list_all()
        docs = [star_to_doc_dict(d) for d in stars]

        provider = None if no_llm else detect_provider()
        if provider is None:
            kw_results = extract_keywords_tf_idf(docs, top_n=50, min_df=2)
            kw_method = "TF-IDF"
        else:
            kw_results = extract_keywords_via_llm(docs, provider=provider, max_keywords=50)
            kw_method = f"LLM ({provider.value})"
        kw_repo = KeywordRepository(s)
        n_kws = kw_repo.bulk_upsert_from_tfidf(kw_results, source="auto")

    return {"keywords": n_kws, "kw_method": kw_method}


def run_init(user: str, no_llm: bool = False) -> dict:
    """跑 init(组合:拉 star + 提取关键字)。scheduler 与 CLI 仍用,前端不再调用。

    顺序:fetch_stars → extract_keywords。任一失败抛错。
    """
    fetch_result = run_fetch_stars(user=user)
    kw_result = run_extract_keywords(no_llm=no_llm)
    return {
        "user": fetch_result["user"],
        "stars": fetch_result["stars"],
        "keywords": kw_result["keywords"],
        "kw_method": kw_result["kw_method"],
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


# ---------------------------------------------------------------------------
# LLM 仓库简介 / 关键字 rationale (T130)
# ---------------------------------------------------------------------------


def run_summarize(scope: str = "stars", only_missing: bool = True, limit: int = 100) -> dict:
    """LLM 生成仓库简介 / 关键字 rationale(根据 scope 路由)。

    - scope="stars":遍历 Star 表,用 description+topics+language 生成 1-3 句中文摘要
    - scope="keywords":遍历 Keyword 表,基于用户 star 画像生成"为何提取"理由
    - only_missing=True:只处理还没 summary/rationale 的(省 quota)
    - limit:单 job 最多处理 N 条(避免长跑)
    """
    from ai_github_radar.llm.summarizer import (
        LLMProviderError,
        explain_keyword,
        summarize_repo,
    )
    from ai_github_radar.storage.db import session_scope
    from ai_github_radar.storage.repositories import KeywordRepository, StarRepository

    if scope == "stars":
        return _run_summarize_stars(only_missing, limit, summarize_repo, LLMProviderError)
    elif scope == "keywords":
        return _run_summarize_keywords(
            only_missing, limit, explain_keyword, LLMProviderError, StarRepository, KeywordRepository,
        )
    else:
        raise ValueError(f"unknown scope {scope!r}; valid: stars, keywords")


def _star_cls():
    from ai_github_radar.db.models import Star
    return Star


def _kw_cls():
    from ai_github_radar.db.models import Keyword
    return Keyword


def _run_summarize_stars(only_missing, limit, summarize_repo, LLMProviderError):
    """生成 Star.summary。

    简化版:description + topics + language 已够 1-3 句摘要,
    没有 fetch README(避免额外 HTTP + GitHub rate limit)。
    """
    from ai_github_radar.storage.db import session_scope
    from ai_github_radar.storage.repositories import StarRepository

    processed = 0
    failed = 0
    errors: list[str] = []

    with session_scope() as s:
        repo = StarRepository(s)
        if only_missing:
            stars = repo.list_missing_summary(limit=limit)
        else:
            stars = repo.list_all()[:limit]

    log.info("summarize stars: %d candidates (only_missing=%s)", len(stars), only_missing)

    for star in stars:
        # topics 可能是 str(JSON / comma-separated) 或 list
        topics_raw = star.topics or ""
        if isinstance(topics_raw, list):
            topics_list = topics_raw
        elif isinstance(topics_raw, str) and topics_raw:
            import json as _json
            try:
                parsed = _json.loads(topics_raw)
                topics_list = parsed if isinstance(parsed, list) else []
            except (ValueError, _json.JSONDecodeError):
                topics_list = [t.strip() for t in topics_raw.split(",") if t.strip()]
        else:
            topics_list = []

        try:
            result = summarize_repo(
                full_name=star.full_name,
                description=star.description,
                language=star.language,
                topics=topics_list,
                readme_excerpt="",
            )
        except Exception as e:  # noqa: BLE001
            failed += 1
            if len(errors) < 3:
                errors.append(f"{star.full_name}: {type(e).__name__}: {e}")
            log.warning("summarize %s failed: %s", star.full_name, e)
            continue

        with session_scope() as s2:
            star_db = s2.get(_star_cls(), star.id)
            if star_db is None:
                continue
            from datetime import datetime
            star_db.summary = result.summary
            star_db.summary_model = result.model
            star_db.summary_at = datetime.utcnow().isoformat(timespec="seconds")
        processed += 1

    return {
        "scope": "stars",
        "processed": processed,
        "failed": failed,
        "candidates": len(stars),
        "errors": errors,
    }


def _run_summarize_keywords(
    only_missing, limit, explain_keyword, LLMProviderError,
    StarRepository, KeywordRepository,
):
    """生成 Keyword.rationale — 基于用户 star 仓库的整体描述。"""
    from ai_github_radar.storage.db import session_scope

    # 1. 抽用户的 star descriptions 作为上下文(全局一次)
    with session_scope() as s:
        star_repo = StarRepository(s)
        sample_descs = [sd for sd in star_repo.all_descriptions(limit=30) if sd]
        n_stars = star_repo.count_all()

        kw_repo = KeywordRepository(s)
        if only_missing:
            kws = kw_repo.list_missing_rationale(limit=limit)
        else:
            kws = kw_repo.list_all()[:limit]

    log.info(
        "summarize keywords: %d candidates, %d sample descriptions",
        len(kws), len(sample_descs),
    )

    processed = 0
    failed = 0
    errors: list[str] = []

    for kw in kws:
        try:
            rationale = explain_keyword(
                term=kw.term,
                sample_descriptions=sample_descs,
                n_stars=n_stars,
            )
        except Exception as e:  # noqa: BLE001
            failed += 1
            if len(errors) < 3:
                errors.append(f"{kw.term}: {type(e).__name__}: {e}")
            log.warning("explain %s failed: %s", kw.term, e)
            continue

        with session_scope() as s2:
            k = s2.get(_kw_cls(), kw.id)
            if k is None:
                continue
            k.rationale = rationale
        processed += 1

    return {
        "scope": "keywords",
        "processed": processed,
        "failed": failed,
        "candidates": len(kws),
        "errors": errors,
    }