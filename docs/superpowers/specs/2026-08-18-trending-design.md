# Spec — T005 github/trending.py

| 维度 | 内容 |
|---|---|
| **TODO ID** | T005（docs/TODO.md §基础设施） |
| **作者** | ai-github-radar 维护者 + AI 助手（2026-08-18） |
| **优先级** | 高 — scan 命令核心依赖 |
| **触发** | docs/TODO.md T005 + 用户扩展需求「关键词查询 + star 阈值筛选」 |

---

## B1. 设计

### 1.1 目标

实现 `src/ai_github_radar/github/trending.py`，**两条互补的抓取路径**：

| 路径 | 数据源 | 适用场景 |
|---|---|---|
| **`fetch_trending_html(lang, since)`** | `httpx` GET `https://github.com/trending` + `bs4` 解析 | 通用「今天 GitHub 上什么火」（主路径） |
| **`search_repositories(keywords, min_stars, language, sort)`** | `httpx` GET `https://api.github.com/search/repositories` | 按用户关键字 + 阈值过滤（精准推荐） |

`trending_html` 是**被动发现**（不知道用户关注什么，全网 hot 是什么），`search_repositories` 是**主动检索**（用户配置关键词后精准查）。

### 1.2 fetch_trending_html

```python
def fetch_trending_html(
    language: str | None = None,    # "python" / "rust" / None(全语言)
    since: str = "daily",           # "daily" | "weekly" | "monthly"
    *,
    client: httpx.Client | None = None,  # 测试注入
) -> list[dict]:
    """拉 GitHub trending 页 HTML 并解析。返回 list[dict]。

    dict 字段(对齐 TrendingSnapshot ORM):
      - repo_id:int          # 从 HTML 解析 full_name 后暂用 0 占位(HTML 无 id)
      - full_name:str        # "owner/name"
      - description:str|None
      - language:str|None
      - stars_today:int|None # HTML 中是 "1,234 stars today"
      - rank:int             # 1..25
      - fetched_at:str       # ISO
    """
```

**实现要点**：
- 用 `httpx.Client` 同步请求(测试用 respx 拦截)
- 设置 `User-Agent: ai-github-radar/0.1` —— GitHub 不拦截 UA 规范的客户端
- bs4 选择器：`article.Box-row`(2026 验证可用,如不可用按 fallback 触发)
- 解析 `stars today`:`h2 + p` 后取 text,正则取数字
- 解析 `language`:`span[itemprop="programmingLanguage"]` 或 `.d-inline .text-gray`
- HTML 解析抛任何 `Exception` → 抛 `TrendingFetchError`(主路径不可用标志)

### 1.3 search_repositories

```python
def search_repositories(
    keywords: list[str],            # 至少 1 个,OR 连接
    *,
    min_stars: int = 0,             # "stars:>=N" 过滤
    language: str | None = None,    # "language:python"
    sort: str = "stars",            # "stars" | "updated" | "forks"
    order: str = "desc",            # "desc" | "asc"
    per_page: int = 30,             # 1..100
    client: httpx.Client | None = None,
) -> list[dict]:
    """用 GitHub search API 按关键词+阈值检索。

    返回 list[dict],字段同 fetch_trending_html(repo_id 从 API 拿真值)。
    """
```

**实现要点**：
- 构造 query:`{"KEYWORD1 OR KEYWORD2"} language:python stars:>=100`(关键字部分必须大括号包裹,OR 才生效)
- 401/403/429 → `GitHubRateLimitError`(复用 T004 的错误类型)
- 429 retry:指数退避 1s/2s/4s,最多 3 次,仍 429 抛错
- 200 解析 JSON `items` 数组
- API 返回的 repo 字段映射到统一的 dict 格式(与 fetch_trending_html 一致)

### 1.4 路径协调(由调用方决定,trending.py 自身不做)

`scan` 命令(T012)的伪代码:
```python
trending = fetch_trending_html()          # 主路径
if not trending:
    # fallback: 用用户关键词 search
    trending = search_repositories(
        keywords=user_keywords,
        min_stars=10,
    )
```

具体编排属于 T012,T005 仅暴露两个独立 API。

### 1.5 非目标

- ❌ 自动 fallback 编排(T012 编排,trending.py 只暴露两个独立 API)
- ❌ 缓存 trending 结果(每次 scan 都拉最新)
- ❌ WebSocket / streaming
- ❌ 拉非 trending 页面(stars / followers / etc)

---

## B2. 验收

| AC | 断言 | 怎么验 |
|---|---|---|
| AC-1 | `fetch_trending_html()` 返回 list[dict],len ≥ 20 | respx mock trending HTML 含 25 article → 返回 len == 25 |
| AC-2 | dict 字段对齐 TrendingSnapshot ORM | 单测:字段集合 ⊇ ORM 必需字段 |
| AC-3 | `language="python"` 传给请求 URL 带 `?since=daily&spoken_language_code=` 之外加 `python` 路径 | respx 看 URL |
| AC-4 | `since="weekly"` URL 含 `/trending/weekly` 或 `since=weekly` | respx |
| AC-5 | HTML 解析失败(结构变化)抛 `TrendingFetchError` | 单测:传空 HTML → 抛错 |
| AC-6 | `search_repositories(["agent","claude"], min_stars=10)` URL 含 `agent OR claude` + `stars:>=10` | respx 看 URL |
| AC-7 | `language="rust"` + `keywords=["async"]` URL 含 `language:rust` + `async` | respx |
| AC-8 | 401 → GitHubRateLimitError | respx 401 |
| AC-9 | 429 重试 3 次仍失败 → GitHubRateLimitError 且 attempts == 3 | respx 429 + 时间 mock |
| AC-10 | 200 解析 `items` 字段,字段映射对齐 | respx mock 真实 API JSON |
| AC-11 | `per_page=50` URL 含 `per_page=50` | respx |
| AC-12 | 空 keywords → 抛 `ValueError` | 单测 |

---

## B3. 测试矩阵

| C | 维度 | 覆盖 |
|---|---|---|
| C1 功能 | fetch_trending_html happy path | AC-1 |
| C2 功能 | 字段映射 | AC-2 |
| C3 功能 | language / since 参数传 URL | AC-3 / AC-4 |
| C4 错误 | HTML 解析失败 | AC-5 |
| C5 功能 | search_repositories keywords URL | AC-6 |
| C6 功能 | language 过滤 | AC-7 |
| C7 错误 | 401 错误路径 | AC-8 |
| C8 错误 | 429 retry 3 次 | AC-9 |
| C9 功能 | 200 解析 items | AC-10 |
| C10 边界 | per_page 参数 | AC-11 |
| C11 边界 | 空 keywords 校验 | AC-12 |
| C12 一致性 | 两个 API 返回 dict 字段一致 | 单测:相同字段集合 |

测试文件:`tests/unit/github/test_trending.py`(用 respx mock httpx)

---

## B4. 风险

- **R1**：GitHub trending HTML 结构变动(每年 ~1-2 次)。**缓解**:bs4 解析失败抛 TrendingFetchError,由 T012 编排 fallback。
- **R2**：GitHub API 未鉴权限流 10 req/min(认证后 30 req/min)。**缓解**:指数退避 3 次,daemon 周期 24h 实际请求极少。
- **R3**：search API `q=` 长度上限 ~256 字符。**缓解**:单测覆盖 200 关键字也不超。
- **R4**：respx 0.21 拦截 httpx,pyproject 已声明 respx≥0.21,依赖装齐。
- **R5**：bs4 选择器 `article.Box-row` 可能在 GitHub 改版后失效。**缓解**:用 find_all fallback + 测试 fixture 真实 HTML 快照。