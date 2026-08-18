# Spec — T004 github/client.py

| 维度 | 内容 |
|---|---|
| **TODO ID** | T004（docs/TODO.md §基础设施） |
| **作者** | ai-github-radar 维护者 + AI 助手（2026-08-18） |
| **优先级** | 高 — `init` 命令核心依赖 |
| **触发** | docs/TODO.md T004 |

---

## B1. 设计

### 1.1 目标

实现 `src/ai_github_radar/github/__init__.py` + `client.py`：
- `GitHubClient` 类：封装 PyGithub `Github` 实例
- `fetch_stars(user)` → `list[dict]`：拉 `/users/{user}/starred` 全量,每个 star 转 dict
- 单个 star dict 字段对应 `Star` ORM 模型字段(便于直接入库)
- 提供 `get_client(token: str)` 工厂 + `from_settings()` 工厂(从 config 读 token)
- 429/403 错误抛 `GitHubRateLimitError`(带 retry-after 信息)
- 网络错误抛 `GitHubNetworkError`

### 1.2 Star dict 字段

| dict key | ORM 字段 | 类型 |
|---|---|---|
| repo_id | repo_id | int |
| owner | owner | str |
| name | name | str |
| full_name | full_name | str |
| description | description | str\|None |
| language | language | str\|None |
| topics | topics | list[str] |
| homepage | homepage | str\|None |
| stargazers_count | stargazers_count | int |
| pushed_at | pushed_at | str (ISO) |
| starred_at | starred_at | str (ISO) |
| archived | archived | bool |

### 1.3 非目标

- ❌ Trending 抓取(T005)
- ❌ search API(T008 recommender 用)
- ❌ 增量刷新(stars 表全量刷,见 docs/database-design.md)
- ❌ 写库(client 只返回 dict,入库由 init 命令编排,T012)

### 1.4 API 契约

```python
class GitHubRateLimitError(Exception):
    """429 / secondary rate limit / abuse detection."""

class GitHubNetworkError(Exception):
    """网络层失败(连接超时 / DNS / etc)。"""

class GitHubClient:
    def __init__(self, token: SecretStr | str): ...

    def fetch_stars(self, user: str, *, max_pages: int | None = None) -> list[dict]:
        """拉用户所有 star 的元数据。

        max_pages: 测试用,限制页数避免真实全量请求。
        返回 list[dict],每个 dict 字段见 §1.2。
        """

def from_settings() -> GitHubClient:
    """从 load_settings() 构造 client(方便 init 命令调用)。"""
```

---

## B2. 验收

| AC | 断言 | 怎么验 |
|---|---|---|
| AC-1 | 合法 token + 合法 user → 返回 list[dict] 且 len ≥ 1 | respx mock `/user/starred` 返回 1 个 fixture repo → `fetch_stars` 返回 1 dict |
| AC-2 | dict 字段 == §1.2 表 | 单测:字段集合 ⊇ 表 |
| AC-3 | `topics` 是 list[str](PyGithub 返回 list) | 单测:len(dict["topics"]) ≥ 0 |
| AC-4 | 401 / 403 → GitHubRateLimitError | respx mock 401 → 抛 RateLimitError |
| AC-5 | 429 → GitHubRateLimitError(retry-after 解析) | respx mock 429 with Retry-After header → 抛 RateLimitError 且 .retry_after 属性 |
| AC-6 | 网络错误 → GitHubNetworkError | respx mock connect error → 抛 NetworkError |
| AC-7 | max_pages=1 限制只拉 1 页 | respx mock 2 页 → 返回值只含第 1 页 |
| AC-8 | `from_settings()` 用 config 的 token | 单测:patch settings → 验证传给 Github 的 token 一致 |

---

## B3. 测试矩阵

| C | 维度 | 覆盖 |
|---|---|---|
| C1 功能 | happy path | AC-1 |
| C2 功能 | dict 字段映射 | AC-2 |
| C3 边界 | topics 列表 | AC-3 |
| C4 错误 | 401/403/429 错误路径 | AC-4 / AC-5 |
| C5 错误 | 网络失败 | AC-6 |
| C6 边界 | max_pages 限制 | AC-7 |
| C7 集成 | from_settings 集成 config | AC-8 |
| C8 一致性 | PyGithub lazy pagination 行为 | 单测:多页场景下拉到底 |
| C9 错误 | 404 user not found → 抛 ValueError | 单测 |
| C10 一致性 | repo dict JSON-serializable(便于持久化) | 单测:json.dumps 不抛 |

测试文件：`tests/unit/github/test_client.py`

---

## B4. 风险

- **R1**：PyGithub 在单元测试里很难直接 mock（内部用 requests）。**缓解**：用 respx mock httpx；PyGithub 实际依赖 `requests`，respx 不能直接拦截 requests（仅 httpx）。需用 `unittest.mock.patch` mock PyGithub.Github.get_user().get_starred()。
- **R2**：宿主机 py3.9 不一定装 PyGithub。**缓解**：本 spec 实现尽量不引入 PyGithub 的复杂类型，client 仅用 `Github.get_user().get_starred()` 返回的 PaginatedList。
- **R3**：GitHub `/user/starred` 返回顺序是按 starred_at desc，但 PyGithub 自动分页。**缓解**：测试不假设顺序，只断言 set equality。