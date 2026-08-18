# Spec — T006 keywords/extractor.py

| 维度 | 内容 |
|---|---|
| | **TODO ID** | T006（docs/TODO.md §业务核心） |
| **作者** | ai-github-radar 维护者 + AI 助手（2026-08-18） |
| **优先级** | 高 — 关键字是 scan 匹配的核心输入 |
| **触发** | docs/TODO.md T006 |

---

## B1. 设计

### 1.1 目标

实现 `src/ai_github_radar/keywords/`：
- `__init__.py` — 暴露 `extract_keywords_tf_idf` / `KeywordRepository` / 关键字 CRUD
- `extractor.py` — TF-IDF 提取器 + 文本预处理
- `repository.py` — Keyword ORM CRUD(基于 T003 的 Base + session_scope)

### 1.2 extractor.py API

```python
def extract_keywords_tf_idf(
    docs: list[str],                      # 每个 star 的描述+topics+language 拼成的文本
    *,
    top_n: int = 50,                      # 提取前 N 个
    min_df: int = 2,                      # 最小文档频率(过滤只出现 1 次的噪声词)
    ngram_range: tuple[int, int] = (1, 2),  # 1-gram + 2-gram
    stop_words: set[str] | None = None,   # 自定义停用词
) -> list[tuple[str, float]]:             # [(term, weight), ...] 按 weight 降序
    """TF-IDF 提取关键字。

    实现:
      - sklearn.feature_extraction.text.TfidfVectorizer
      - 文本预处理:小写 + 去标点 + 英文分词(ngram 模式)
      - weight = 该词在所有文档里的 TF-IDF 平均值
      - 输出按 weight 降序
    """
```

**中文 / GitHub 特殊词**:GitHub 仓库描述以英文为主,TF-IDF 用英文 ngram 即可;保留 `MCP` / `LLM` / `AI` 等大写词(token_pattern 默认会过滤)。

### 1.3 repository.py API

```python
class KeywordRepository:
    """Keyword ORM CRUD + 业务编排。

    所有写操作在调用方传入的 session_scope 内执行(本类不创建 session)。
    """

    def __init__(self, session: Session):
        self._s = session

    # ---- read ----
    def list(self, *, enabled_only: bool = False) -> list[Keyword]: ...
    def get_by_term(self, term: str) -> Keyword | None: ...
    def get_by_id(self, kw_id: int) -> Keyword | None: ...

    # ---- write ----
    def upsert(self, term: str, weight: float = 1.0, source: str = "manual") -> Keyword:
        """按 term 唯一约束:已存在则更新 weight,不存在则插入。"""

    def add(self, term: str, weight: float = 1.0, source: str = "manual") -> Keyword:
        """纯 insert,term 已存在抛 IntegrityError。"""

    def delete(self, term_or_id: str | int) -> bool:
        """按 term 或 id 删除,返回是否真删了。"""

    def toggle(self, term_or_id: str | int) -> Keyword | None:
        """翻转 enabled 字段,返回新实例或 None(不存在)。"""

    # ---- 批量 ----
    def bulk_upsert_from_tfidf(
        self,
        tfidf_results: list[tuple[str, float]],
        *,
        source: str = "auto",
    ) -> int:
        """把 TF-IDF 结果 upsert 到 DB,返回 upsert 数量。

        weight 取 TF-IDF 分数 * 10 归一化到 1.0-10.0。
        """
```

### 1.4 非目标

- ❌ LLM 升级路径(T007 `keywords/llm_upgrade.py`)
- ❌ CLI 编排(`keyword list/add/del/toggle`,T012)
- ❌ 关键字去重 / 合并近义词(阶段二 T203)

---

## B2. 验收

| AC | 断言 | 怎么验 |
|---|---|---|
| AC-1 | `extract_keywords_tf_idf()` 返回 list[(term, weight)] 按 weight 降序 | 单测:构造 3 文档 → 验证返回顺序 |
| AC-2 | top_n 参数生效 | 单测:top_n=3 → 返回 len ≤ 3 |
| AC-3 | min_df 过滤低频词 | 单测:只出现 1 次的词被滤掉 |
| AC-4 | ngram_range=(1,1) 只返单词 | 单测:无 2-gram |
| AC-5 | ngram_range=(1,2) 含 1-gram + 2-gram | 单测:返 ngram 字符串含空格 |
| AC-6 | stop_words 过滤停用词 | 单测:停用词不在返回 |
| AC-7 | `repo.list()` 返回所有关键字 | 单测:seed 3 → list 3 |
| AC-8 | `repo.list(enabled_only=True)` 过滤 disabled | 单测:seed 3 含 1 个 enabled=False → list 2 |
| AC-9 | `repo.upsert` 已存在更新 weight | 单测:插入后改 weight → 第二次 upsert 后 weight 更新 |
| AC-10 | `repo.add` term 已存在抛 IntegrityError | 单测 |
| AC-11 | `repo.delete(term)` 返回 True | 单测 |
| AC-12 | `repo.delete` 不存在返 False | 单测 |
| AC-13 | `repo.toggle` 翻转 enabled | 单测:True→False→True |
| AC-14 | `bulk_upsert_from_tfidf` 返回 upsert 数量 | 单测:5 个 TF-IDF 结果 → 返回 5 |
| AC-15 | `init` 流程(50 star → TF-IDF → repository)产出 ≥ 30 keywords | 集成测试 fixture:50 个真实化 star dict,跑 TF-IDF + bulk_upsert,assert ≥ 30 |

---

## B3. 测试矩阵

| C | 维度 | 覆盖 |
|---|---|---|
| C1 功能 | TF-IDF 提取 | AC-1 |
| C2 边界 | top_n 限制 | AC-2 |
| C3 边界 | min_df 过滤 | AC-3 |
| C4 边界 | ngram_range | AC-4 / AC-5 |
| C5 边界 | 停用词 | AC-6 |
| C6 功能 | repository CRUD | AC-7..AC-13 |
| C7 功能 | 批量 upsert | AC-14 |
| C8 集成 | init 闭环 | AC-15 |
| C9 错误 | repository 重复 add 抛 IntegrityError | AC-10 |
| C10 一致性 | ORM 字段映射 | 静态检查 + 单测 |

测试文件:`tests/unit/keywords/test_extractor.py` + `tests/unit/keywords/test_repository.py`

---

## B4. 风险

- **R1**：sklearn TF-IDF 在 50-100 文档规模下可能全空(ngram + min_df 过严)。**缓解**：spec 默认 `min_df=2 / ngram=(1,2)`，AC-15 fixture 必须 50+ 真实描述。
- **R2**：GitHub 描述里 emoji / markdown 干扰。**缓解**：文本预处理去 emoji + 去 markdown 符号。
- **R3**：weight 取 TF-IDF 分数 * 10 在分布不均时可能爆。**缓解**：归一化到 1.0-10.0(`min(weight * 10, 10.0)`)。
- **R4**：repository 测试要 in-memory SQLite。**缓解**：复用 T003 的 engine fixture,加 `:memory:`。