"""FastAPI 本地 UI — T013."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

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