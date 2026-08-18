# Spec — T013 web/

| 维度 | 内容 |
|---|---|
| **TODO ID** | T013（docs/TODO.md §收尾） |
| **作者** | ai-github-radar 维护者 + AI 助手（2026-08-19） |
| **优先级** | 中 — 本地浏览，可选 |
| **触发** | docs/TODO.md T013 + 用户扩展 web UI |

---

## B1. 设计

### 1.1 目标

实现 `src/ai_github_radar/web/`,**FastAPI 本地 UI**:

| 端点 | 内容 |
|---|---|
| `GET /` | 渲染推荐列表（HTML） |
| `GET /keywords` | 关键字表（HTML） |
| `GET /api/recommendations` | JSON 推荐列表（最近 7 天） |
| `GET /api/keywords` | JSON 关键字列表 |
| `POST /api/keywords` | 加关键字（JSON body: `{term, weight}`） |
| `DELETE /api/keywords/{term}` | 删 |
| `POST /api/keywords/{term}/toggle` | toggle enabled |
| `POST /api/scan` | 触发 scan（同步返回 recs 列表） |

服务用 `uvicorn` 跑（pyproject 已声明）。

### 1.2 静态文件

`src/ai_github_radar/web/static/` 提供 CSS/JS，但本期 **不实现**（模板内联 minimal CSS）。

### 1.3 API 入口

```python
def create_app() -> FastAPI:
    """FastAPI 应用工厂。"""

def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    """uvicorn.run 阻塞入口(供 cli/web 命令调)。"""
```

### 1.4 非目标

- ❌ 实时 WebSocket 推送
- ❌ 用户认证（默认 127.0.0.1）
- ❌ 异步后台任务（同步触发 scan）

---

## B2. 验收

| AC | 断言 | 怎么验 |
|---|---|---|
| AC-1 | create_app() 返回 FastAPI 实例 | 单测 |
| AC-2 | GET / 返回 HTML 含 "GitHub Radar" | TestClient |
| AC-3 | GET /keywords 返回 HTML 含关键字表 | TestClient |
| AC-4 | GET /api/keywords 返回 JSON list | TestClient |
| AC-5 | GET /api/recommendations 返回 JSON list | TestClient |
| AC-6 | POST /api/keywords 入库 | TestClient + DB 检查 |
| AC-7 | DELETE /api/keywords/{term} 删 | TestClient |
| AC-8 | POST /api/keywords/{term}/toggle 翻转 | TestClient |
| AC-9 | POST /api/scan 触发 scan 返回 recs | mock + TestClient |
| AC-10 | 404 path 返 404 | TestClient |

---

## B3. 测试矩阵

| C | 维度 | 覆盖 |
|---|---|---|
| C1 创建 | create_app() | AC-1 |
| C2 HTML | / 和 /keywords | AC-2 / AC-3 |
| C3 API 读 | /api/keywords + /api/recommendations | AC-4 / AC-5 |
| C4 API 写 | POST/DELETE/toggle | AC-6 / AC-7 / AC-8 |
| C5 API 触发 | scan | AC-9 |
| C6 错误 | 404 | AC-10 |

测试文件：`tests/unit/web/test_app.py`

---

## B4. 风险

- **R1**：FastAPI TestClient 需要 asgi 同步环境，pytest 已支持。
- **R2**：scan 端点调用 cli.scan_cmd 逻辑，复用 session_scope 隔离。
- **R3**：测试用 in-memory DB（reset_for_testing + cwd tmp）。