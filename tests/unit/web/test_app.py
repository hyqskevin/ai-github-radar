"""T013 web/app.py 测试。

用 in-memory DB(TestClient + reset_for_testing + cwd-relative tmp DB)。
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from ai_github_radar.web import create_app


@pytest.fixture()
def client(tmp_path):
    """构造 TestClient + 隔离 cwd + in-memory-like 真实 sqlite。"""
    cwd_orig = os.getcwd()
    os.chdir(str(tmp_path))
    from ai_github_radar.storage.db import reset_for_testing, init_db
    reset_for_testing()
    init_db()
    app = create_app()
    yield TestClient(app)
    os.chdir(cwd_orig)


def test_ac1_create_app_returns_fastapi() -> None:
    """AC-1: create_app() 返回 FastAPI 实例。"""
    from fastapi import FastAPI
    app = create_app()
    assert isinstance(app, FastAPI)


def test_ac2_root_html_contains_title(client: TestClient) -> None:
    """AC-2: GET / 返回 HTML 含 "GitHub Radar"。"""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "GitHub Radar" in resp.text


def test_ac3_keywords_html_table(client: TestClient) -> None:
    """AC-3: GET /keywords 返回 HTML 表。"""
    # 先 seed 一个 keyword
    client.post("/api/keywords", json={"term": "agent", "weight": 5.0})
    resp = client.get("/keywords")
    assert resp.status_code == 200
    assert "关键字" in resp.text or "keywords" in resp.text.lower()
    assert "agent" in resp.text


def test_ac4_api_keywords_list(client: TestClient) -> None:
    """AC-4: GET /api/keywords 返回 JSON list。"""
    client.post("/api/keywords", json={"term": "agent"})
    client.post("/api/keywords", json={"term": "claude"})
    resp = client.get("/api/keywords")
    assert resp.status_code == 200
    data = resp.json()
    assert "keywords" in data
    assert len(data["keywords"]) == 2
    terms = {k["term"] for k in data["keywords"]}
    assert terms == {"agent", "claude"}


def test_ac5_api_recommendations_list(client: TestClient) -> None:
    """AC-5: GET /api/recommendations 返回 JSON list。"""
    resp = client.get("/api/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)


def test_ac6_api_add_keyword(client: TestClient) -> None:
    """AC-6: POST /api/keywords 入库。"""
    resp = client.post("/api/keywords", json={"term": "fastapi", "weight": 5.0})
    assert resp.status_code == 201
    data = resp.json()
    assert data["term"] == "fastapi"
    assert data["weight"] == 5.0
    # 验证在 list 里
    listing = client.get("/api/keywords").json()
    assert any(k["term"] == "fastapi" for k in listing["keywords"])


def test_ac6_api_add_duplicate_returns_409(client: TestClient) -> None:
    """重复 add → 409。"""
    client.post("/api/keywords", json={"term": "agent"})
    resp = client.post("/api/keywords", json={"term": "agent"})
    assert resp.status_code == 409


def test_ac7_api_delete_keyword(client: TestClient) -> None:
    """AC-7: DELETE /api/keywords/{term} 删。"""
    client.post("/api/keywords", json={"term": "to_del"})
    resp = client.delete("/api/keywords/to_del")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": "to_del"}
    listing = client.get("/api/keywords").json()
    assert all(k["term"] != "to_del" for k in listing["keywords"])


def test_ac7_api_delete_missing_returns_404(client: TestClient) -> None:
    """删除不存在的 term → 404。"""
    resp = client.delete("/api/keywords/never_existed")
    assert resp.status_code == 404


def test_ac8_api_toggle_keyword(client: TestClient) -> None:
    """AC-8: POST /api/keywords/{term}/toggle 翻转 enabled。"""
    client.post("/api/keywords", json={"term": "agent"})
    resp = client.post("/api/keywords/agent/toggle")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False
    # 再 toggle 一次
    resp2 = client.post("/api/keywords/agent/toggle")
    assert resp2.json()["enabled"] is True


def test_ac9_api_trigger_scan(client: TestClient) -> None:
    """AC-9: POST /api/scan 触发 scan 返回 recs(空 trending 也合法)。"""
    client.post("/api/keywords", json={"term": "agent", "weight": 5.0})
    resp = client.post("/api/scan", json={"top": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)


def test_ac10_404_unknown_path(client: TestClient) -> None:
    """AC-10: 未知 path → 404。"""
    resp = client.get("/this/does/not/exist")
    assert resp.status_code == 404


def test_openapi_docs_available(client: TestClient) -> None:
    """/docs 路由可访问(FastAPI 自动)。"""
    resp = client.get("/docs")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# T138 — /api/stars 分页(total / offset / 空库)
# ---------------------------------------------------------------------------


def _seed_stars(client: TestClient, n: int) -> None:
    """直接向当前 DB 插入 n 条 Star(绕过 GitHub 拉取)。"""
    from ai_github_radar.db.models import Star
    from ai_github_radar.storage.db import session_scope

    with session_scope() as s:
        for i in range(n):
            s.add(Star(
                repo_id=i + 1,
                owner="o",
                name=f"r{i}",
                full_name=f"o/r{i}",
                description=f"repo {i}",
            ))


def test_ac1_stars_pagination_returns_total(client: TestClient) -> None:
    """T138 AC-1: limit+offset 生效且返回 total。"""
    _seed_stars(client, 3)
    resp = client.get("/api/stars?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["stars"]) == 2
    assert data["total"] == 3
    assert data["limit"] == 2
    assert data["offset"] == 0


def test_ac_stars_offset_no_overlap(client: TestClient) -> None:
    """T138 AC-2: offset 翻页不重叠。"""
    _seed_stars(client, 3)
    page1 = client.get("/api/stars?limit=2&offset=0").json()["stars"]
    page2 = client.get("/api/stars?limit=2&offset=2").json()["stars"]
    id1 = {r["repo_id"] for r in page1}
    id2 = {r["repo_id"] for r in page2}
    assert len(id1 & id2) == 0
    assert len(page1) == 2
    assert len(page2) == 1  # 3 条里只剩最后一条


def test_ac_stars_total_zero_when_empty(client: TestClient) -> None:
    """T138 AC-4: 空库 total=0,stars=[]。"""
    resp = client.get("/api/stars?limit=2&offset=0")
    data = resp.json()
    assert data["stars"] == []
    assert data["total"] == 0