"""FastAPI 本地 UI — T013."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

log = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """FastAPI 应用工厂。"""
    app = FastAPI(
        title="ai-github-radar",
        description="GitHub 趋势追踪 + 推荐",
        version="0.1.0",
    )

    app.include_router(html_router)
    app.include_router(api_router)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        log.exception("unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "internal", "detail": str(exc)},
        )

    return app


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    """uvicorn.run 阻塞入口。"""
    import uvicorn
    uvicorn.run(create_app(), host=host, port=port, log_level="info")


# ---------------------------------------------------------------------------
# HTML 模板(inline)
# ---------------------------------------------------------------------------

from fastapi import APIRouter  # noqa: E402

html_router = APIRouter()


_HTML_INDEX = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>GitHub Radar — 推荐</title>
  <style>
    body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; color: #24292e; }}
    h1 {{ border-bottom: 1px solid #eee; padding-bottom: 8px; }}
    .rec {{ border: 1px solid #ddd; border-radius: 6px; padding: 12px; margin: 12px 0; }}
    .rec h3 {{ margin: 0 0 6px 0; }}
    .rec a {{ color: #0366d6; text-decoration: none; }}
    .meta {{ color: #666; font-size: 13px; }}
    nav {{ margin: 16px 0; }}
    nav a {{ margin-right: 16px; color: #0366d6; }}
  </style>
</head>
<body>
  <h1>GitHub Radar — 推荐 ({date})</h1>
  <nav>
    <a href="/">推荐</a>
    <a href="/keywords">关键字</a>
    <a href="/api/recommendations">API</a>
    <a href="/docs">FastAPI Docs</a>
  </nav>
  {body}
</body>
</html>
"""


@html_router.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    """首页:今日推荐列表。"""
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.storage.repositories import RecommendationRepository

    init_db()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with session_scope() as s:
        recs = s.execute(
            __import__("sqlalchemy").text(
                "SELECT repo_id, score, matched_keywords, channel, pushed_at "
                "FROM recommendations ORDER BY pushed_at DESC LIMIT 50"
            )
        ).fetchall()
    body = "<p>暂无推荐</p>"
    if recs:
        items = []
        for r in recs:
            kw_text = (r.matched_keywords or "").replace(",", " · ")
            items.append(
                f'<div class="rec"><h3><a href="https://github.com/repo/{r.repo_id}">'
                f'#{r.repo_id}</a></h3>'
                f'<div class="meta">score={r.score:.3f} · {r.channel} · {r.pushed_at}</div>'
                f'<div>matched: {kw_text}</div></div>'
            )
        body = "\n".join(items)
    return HTMLResponse(_HTML_INDEX.format(date=today, body=body))


_HTML_KEYWORDS = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>GitHub Radar — 关键字</title>
  <style>
    body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 8px; border-bottom: 1px solid #eee; text-align: left; }}
    th {{ background: #f6f8fa; }}
    .enabled-true {{ color: #22863a; }}
    .enabled-false {{ color: #b31d28; }}
    nav {{ margin: 16px 0; }}
    nav a {{ margin-right: 16px; color: #0366d6; }}
  </style>
</head>
<body>
  <h1>关键字</h1>
  <nav>
    <a href="/">推荐</a>
    <a href="/keywords">关键字</a>
  </nav>
  <table>
    <tr><th>ID</th><th>Term</th><th>Weight</th><th>Source</th><th>Enabled</th></tr>
    {rows}
  </table>
</body>
</html>
"""


@html_router.get("/keywords", response_class=HTMLResponse)
def keywords_page() -> HTMLResponse:
    """关键字列表 HTML。"""
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.storage.repositories import KeywordRepository

    init_db()
    with session_scope() as s:
        kws = KeywordRepository(s).list()
    rows = "\n".join(
        f"<tr><td>{k.id}</td><td>{k.term}</td><td>{k.weight:.2f}</td>"
        f"<td>{k.source}</td>"
        f"<td class='enabled-{str(k.enabled).lower()}'>{k.enabled}</td></tr>"
        for k in kws
    ) or "<tr><td colspan='5'>no keywords</td></tr>"
    return HTMLResponse(_HTML_KEYWORDS.format(rows=rows))


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

api_router = APIRouter(prefix="/api")


class KeywordIn(BaseModel):
    term: str
    weight: float = 1.0


class ScanRequest(BaseModel):
    top: int = 10
    push: str = "stdout"


def _kw_to_dict(k: Any) -> dict:
    return {
        "id": k.id, "term": k.term, "weight": k.weight,
        "source": k.source, "enabled": k.enabled,
        "created_at": k.created_at, "updated_at": k.updated_at,
    }


@api_router.get("/keywords")
def api_list_keywords() -> dict:
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.storage.repositories import KeywordRepository

    init_db()
    with session_scope() as s:
        kws = KeywordRepository(s).list()
    return {"keywords": [_kw_to_dict(k) for k in kws]}


@api_router.post("/keywords", status_code=201)
def api_add_keyword(body: KeywordIn) -> dict:
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.storage.repositories import KeywordRepository

    init_db()
    with session_scope() as s:
        try:
            kw = KeywordRepository(s).add(body.term, weight=body.weight, source="manual")
        except Exception as e:
            raise HTTPException(status_code=409, detail=f"duplicate or invalid: {e}")
    return _kw_to_dict(kw)


@api_router.delete("/keywords/{term}")
def api_delete_keyword(term: str) -> dict:
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.storage.repositories import KeywordRepository

    init_db()
    with session_scope() as s:
        ok = KeywordRepository(s).delete(term)
    if not ok:
        raise HTTPException(status_code=404, detail=f"not found: {term}")
    return {"deleted": term}


@api_router.post("/keywords/{term}/toggle")
def api_toggle_keyword(term: str) -> dict:
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.storage.repositories import KeywordRepository

    init_db()
    with session_scope() as s:
        kw = KeywordRepository(s).toggle(term)
    if kw is None:
        raise HTTPException(status_code=404, detail=f"not found: {term}")
    return _kw_to_dict(kw)


@api_router.get("/recommendations")
def api_list_recommendations(limit: int = 50) -> dict:
    from sqlalchemy import select
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.db.models import Recommendation

    init_db()
    with session_scope() as s:
        stmt = (
            select(Recommendation)
            .order_by(Recommendation.pushed_at.desc())
            .limit(limit)
        )
        recs = list(s.execute(stmt).scalars())
    return {
        "recommendations": [
            {
                "id": r.id,
                "repo_id": r.repo_id,
                "score": r.score,
                "matched_keywords": (r.matched_keywords or "").split(",") if r.matched_keywords else [],
                "channel": r.channel,
                "pushed_at": r.pushed_at,
            }
            for r in recs
        ]
    }


@api_router.post("/scan")
def api_trigger_scan(body: ScanRequest = ScanRequest()) -> dict:
    """同步触发 scan(轻量版,只返回 recs,不真推送)。"""
    from types import SimpleNamespace
    from sqlalchemy import select
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.storage.repositories import (
        KeywordRepository,
        RecommendationRepository,
        StarRepository,
    )
    from ai_github_radar.recommender.pipeline import rank_recommendations

    init_db()
    with session_scope() as s:
        stars = StarRepository(s).list_all()
        kws = KeywordRepository(s).list(enabled_only=True)
        dedupe = RecommendationRepository(s).recent_repo_ids(days=7)
    # trending 部分本期不实拉(trending 真实 GET 会污染测试),用空 trending
    recs = rank_recommendations(
        stars, [], kws,
        already_recommended_ids=dedupe, top_n=body.top,
    )
    return {"recommendations": recs}


def _star_to_dict(s: Any) -> dict:
    return {
        "id": s.id,
        "repo_id": s.repo_id,
        "owner": s.owner,
        "name": s.name,
        "description": s.description,
        "language": s.language,
        "topics": (s.topics or "").split(",") if getattr(s, "topics", None) else [],
        "starred_at": getattr(s, "starred_at", None).isoformat() if getattr(s, "starred_at", None) else None,
    }


@api_router.get("/stars")
def api_list_stars(limit: int = 200, offset: int = 0) -> dict:
    """列我 star 的仓库(从 SQLite `stars` 表读)。"""
    from sqlalchemy import select
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.db.models import Star

    init_db()
    with session_scope() as s:
        stmt = (
            select(Star)
            .order_by(Star.starred_at.desc().nullslast(), Star.id.desc())
            .limit(limit)
            .offset(offset)
        )
        stars = list(s.execute(stmt).scalars())
    return {"stars": [_star_to_dict(x) for x in stars], "limit": limit, "offset": offset}


@api_router.get("/stars/stats")
def api_stars_stats() -> dict:
    """聚合:总 star 数 + 语言分布 + top topics。"""
    from collections import Counter
    from sqlalchemy import func, select
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.db.models import Star

    init_db()
    with session_scope() as s:
        total = s.execute(select(func.count(Star.id))).scalar() or 0
        rows = s.execute(
            select(Star.language, Star.topics).where(Star.id.isnot(None))
        ).all()
    lang_counter: Counter[str] = Counter()
    topic_counter: Counter[str] = Counter()
    for lang, topics_csv in rows:
        if lang:
            lang_counter[lang] += 1
        if topics_csv:
            for t in topics_csv.split(","):
                t = t.strip()
                if t:
                    topic_counter[t] += 1
    by_language = dict(lang_counter.most_common(15))
    top_topics = [
        {"name": name, "count": cnt}
        for name, cnt in topic_counter.most_common(10)
    ]
    return {
        "total": total,
        "by_language": by_language,
        "top_topics": top_topics,
    }


@api_router.get("/settings/llm")
def api_get_llm_settings() -> dict:
    """读 LLM 设置(provider + model + 是否启用 + API key 是否已设置)。"""
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.services.settings import (
        KEY_LLM_API_KEY,
        KEY_LLM_MODEL,
        KEY_LLM_PROVIDER,
        get_setting,
    )

    init_db()
    with session_scope() as s:
        provider = get_setting(s, KEY_LLM_PROVIDER, "none") or "none"
        model = get_setting(s, KEY_LLM_MODEL, "") or ""
        api_key = get_setting(s, KEY_LLM_API_KEY, "")
    return {
        "provider": provider,
        "model": model,
        "api_key_set": bool(api_key),
        "enabled": provider not in ("none", ""),
    }


@api_router.post("/settings/llm")
def api_set_llm_settings(body: dict) -> dict:
    """持久化 LLM 设置。"""
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.services.settings import (
        KEY_LLM_API_KEY,
        KEY_LLM_MODEL,
        KEY_LLM_PROVIDER,
        set_setting,
    )

    init_db()
    with session_scope() as s:
        if body.get("provider") is not None:
            set_setting(s, KEY_LLM_PROVIDER, body["provider"])
        if body.get("model") is not None:
            set_setting(s, KEY_LLM_MODEL, body["model"])
        if body.get("api_key") is not None:
            # API key 简单存文本(阶段二加 encrypt)
            set_setting(s, KEY_LLM_API_KEY, body["api_key"])
    return api_get_llm_settings()


@api_router.get("/settings/all")
def api_get_all_settings() -> dict:
    """列所有 settings(key-value,API key 隐藏)。"""
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.services.settings import (
        KEY_GITHUB_TOKEN,
        KEY_GITHUB_USER,
        KEY_LLM_API_KEY,
        KEY_LLM_MODEL,
        KEY_LLM_PROVIDER,
        get_setting,
    )

    init_db()
    out = {}
    with session_scope() as s:
        out["llm_provider"] = get_setting(s, KEY_LLM_PROVIDER, "none")
        out["llm_model"] = get_setting(s, KEY_LLM_MODEL, "")
        out["llm_api_key_set"] = bool(get_setting(s, KEY_LLM_API_KEY, ""))
        out["github_user"] = get_setting(s, KEY_GITHUB_USER, "")
        out["github_token_set"] = bool(get_setting(s, KEY_GITHUB_TOKEN, ""))
    return out


@api_router.post("/settings/all")
def api_set_all_settings(body: dict) -> dict:
    """写设置(单字段或全字段都行)。"""
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.services.settings import (
        KEY_GITHUB_TOKEN,
        KEY_GITHUB_USER,
        set_setting,
    )

    init_db()
    with session_scope() as s:
        if "github_user" in body and body["github_user"] is not None:
            set_setting(s, KEY_GITHUB_USER, body["github_user"])
        if "github_token" in body and body["github_token"]:
            set_setting(s, KEY_GITHUB_TOKEN, body["github_token"])
    return api_get_all_settings()


@api_router.get("/health")
def api_health() -> dict:
    """健康检查端点。"""
    return {"status": "ok"}


@api_router.get("/llm/summary")
def api_llm_summary_get() -> dict:
    """LLM summary 占位 — 阶段二接入真实 LLM 调用。"""
    import os

    provider = os.environ.get("LLM_PROVIDER", "none")
    return {
        "provider": provider,
        "model": os.environ.get("LLM_MODEL", ""),
        "enabled": provider != "none",
        "summary": None,
        "note": "阶段一:LLM summary 占位,阶段二接入真实调用",
    }


@api_router.post("/llm/summary")
def api_llm_summary_post(body: dict) -> dict:
    """触发 LLM 生成摘要占位(阶段一不真调用)。"""
    repo_id = body.get("repo_id", "")
    return {
        "repo_id": repo_id,
        "summary": None,
        "provider": "none",
        "saved": False,
        "note": "阶段一:LLM summary 占位,阶段二接入真实调用",
    }


@api_router.get("/jobs")
def api_list_jobs(limit: int = 50) -> dict:
    """列最近任务执行记录(任务监控)。"""
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.services.jobs import job_to_dict, recent_jobs

    init_db()
    with session_scope() as s:
        jobs = recent_jobs(s, limit=limit)
    return {"jobs": [job_to_dict(j) for j in jobs], "limit": limit}


@api_router.post("/jobs/clear")
def api_clear_jobs(body: Optional[dict] = None) -> dict:
    """清空任务记录(可选)。"""
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.db.models import Job

    init_db()
    with session_scope() as s:
        deleted = s.query(Job).delete()
    return {"deleted": deleted}


@api_router.post("/stars/refresh")
def api_refresh_stars(body: Optional[dict] = None) -> dict:
    """后台触发 init(拉 GitHub stars + 提取关键字)。

    body: {user?: str, no_llm?: bool}
    返回: {job_id, status_url} —前端轮询 /api/jobs 查 status。
    """
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.jobs.runner import run_init, submit_task

    body = body or {}
    user = body.get("user") or ""

    init_db()
    with session_scope() as s:
        _, job_id = submit_task(
            "init",
            s,
            run_init,
            user=user,
            no_llm=body.get("no_llm", False),
        )
    return {
        "job_id": job_id,
        "status": "running",
        "poll_url": f"/api/jobs",
    }


@api_router.post("/scan/async")
def api_scan_async(body: Optional[dict] = None) -> dict:
    """后台触发 scan(拉 trending + 匹配 + 写 recommendations)。

    body: {top?: int=10, language?: str, since?: str='daily'}
    """
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.jobs.runner import run_scan, submit_task

    body = body or {}
    top = int(body.get("top", 10))
    language = body.get("language") or None
    since = body.get("since", "daily")

    init_db()
    with session_scope() as s:
        _, job_id = submit_task(
            "scan",
            s,
            run_scan,
            top=top,
            language=language,
            since=since,
        )
    return {
        "job_id": job_id,
        "status": "running",
        "poll_url": f"/api/jobs",
    }


@api_router.get("/schedules")
def api_list_schedules() -> dict:
    """列定时任务 + 计算 next_run_at。"""
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.services.schedules import list_schedules, schedule_to_dict
    from croniter import croniter

    init_db()
    with session_scope() as s:
        scheds = list_schedules(s)
    out = []
    for sc in scheds:
        d = schedule_to_dict(sc)
        if sc.enabled and sc.cron:
            try:
                nxt = croniter(sc.cron, datetime.now(timezone.utc))
                d["next_run_at"] = nxt.get_next(datetime).isoformat()
            except Exception:  # noqa: BLE001
                d["next_run_at"] = None
        out.append(d)
    return {"schedules": out}


@api_router.post("/schedules")
def api_create_schedule(body: dict) -> dict:
    """新增定时任务。body: {name, cron, enabled?, payload?}"""
    from croniter import croniter
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.services.schedules import create_schedule, schedule_to_dict

    name = body.get("name", "").strip()
    cron = body.get("cron", "").strip()
    if not name or not cron:
        raise HTTPException(status_code=400, detail="name + cron required")
    try:
        croniter(cron)  # 校验合法
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid cron: {e}")
    init_db()
    with session_scope() as s:
        sc = create_schedule(
            s,
            name=name,
            cron=cron,
            enabled=body.get("enabled", True),
            payload=body.get("payload"),
        )
    return schedule_to_dict(sc)


@api_router.patch("/schedules/{schedule_id}")
def api_update_schedule(schedule_id: int, body: dict) -> dict:
    """更新定时任务(cron / enabled / payload)。"""
    from croniter import croniter
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.services.schedules import schedule_to_dict, update_schedule

    cron = body.get("cron")
    if cron is not None:
        try:
            croniter(cron)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"invalid cron: {e}")
    init_db()
    with session_scope() as s:
        sc = update_schedule(
            s,
            schedule_id,
            cron=cron,
            enabled=body.get("enabled"),
            payload=body.get("payload"),
        )
    if sc is None:
        raise HTTPException(status_code=404, detail="schedule not found")
    return schedule_to_dict(sc)


@api_router.delete("/schedules/{schedule_id}")
def api_delete_schedule(schedule_id: int) -> dict:
    """删除定时任务。"""
    from ai_github_radar.storage.db import init_db, session_scope
    from ai_github_radar.services.schedules import delete_schedule

    init_db()
    with session_scope() as s:
        ok = delete_schedule(s, schedule_id)
    if not ok:
        raise HTTPException(status_code=404, detail="schedule not found")
    return {"deleted": schedule_id}