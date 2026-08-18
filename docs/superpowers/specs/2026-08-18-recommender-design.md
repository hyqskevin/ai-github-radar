# Spec — T008 recommender/pipeline.py

| 维度 | 内容 |
|---|---|
| **TODO ID** | T008（docs/TODO.md §业务核心） |
| **作者** | ai-github-radar 维护者 + AI 助手（2026-08-18） |
| **优先级** | 高 — 核心匹配算法 |
| **触发** | docs/TODO.md T008 |

---

## B1. 设计

### 1.1 目标

实现 `src/ai_github_radar/recommender/pipeline.py`,**输入三个数据源**:

1. **`Star` 表** —— 用户已 star 的仓库（提供「兴趣关键字」来源）
2. **`TrendingSnapshot` 表** —— 当天 trending 25 条（候选集）
3. **`Keyword` 表** —— 用户显式配置的关键字（订阅源）

输出 `list[dict]`(对齐 `Recommendation` ORM 字段),按 score 降序。

### 1.2 匹配算法

**关键字提取** —— 从 `Star` 表的 `description + topics + language` 拼接文本,跑 `extract_keywords_tf_idf()` (T006)。

**候选打分** —— 对每个 trending repo:

```
score = matched_count * avg_weight * log(stars_today + 2)
       + (description_keywords ∩ user_keywords).count() * 5.0
```

具体计算步骤:

1. **从 trending repo 的 description + topics + language 拼文本**
2. **分词**:小写 + 去标点,与 user_keywords term 做精确匹配(不依赖 tokenizer)
3. **权重**:
   - 命中 user_keywords(显式订阅):每个 +5.0
   - 命中 stars-extracted tfidf(隐式兴趣,weight >= 3.0):每个 `weight * 1.0`
4. **热度加成**:`log(stars_today + 2)`(平滑,避免 0)
5. **过滤**:
   - 跳过**已经在 stars 表里**的 repo(用户已知,无需推荐)
   - 跳过**已经推荐过且 7 天内**的(repo_id, 7-day dedupe)
6. **排序**:按 score 降序,取 top N(默认 10)

### 1.3 API

```python
def rank_recommendations(
    stars: list[Star],                  # 来自 T003 ORM
    trending: list[TrendingSnapshot],   # 来自 T005 解析
    keywords: list[Keyword],            # enabled=True 的用户关键字
    *,
    already_recommended_ids: set[int] | None = None,  # 7-day dedupe,None 跳过
    top_n: int = 10,
    min_score: float = 0.0,             # 过滤 < min_score
    tfidf_top_n: int = 50,              # 从 stars 提多少关键字
) -> list[dict]:
    """主入口。返回 list[dict],字段:
      repo_id, full_name, description, language, score,
      matched_keywords (list[str]), rank, stars_today
    按 score 降序。
    """

def compute_repo_score(
    repo_text: str,                     # "description topics language" 拼成
    user_keywords: dict[str, float],    # term -> weight (TF-IDF weight 或 5.0)
    stars_today: int | None,
) -> tuple[float, list[str]]:
    """单个 repo 的命中分数 + 命中关键字列表。
    供测试和单元复用;rank_recommendations 内部循环调用。
    """
```

### 1.4 字段映射到 ORM

| dict 字段 | Recommendation ORM | 来源 |
|---|---|---|
| `repo_id` | ✓ | trending.repo_id |
| `score` | ✓ | 算法计算 |
| `matched_keywords` | ✓ (JSON str) | 命中 term list |
| `full_name` | - (运行时用) | trending.full_name (拼自 description 旁的元数据,若不可用空) |
| `description` | - | trending.description |
| `language` | - | trending.language |
| `stars_today` | - | trending.stars_today |
| `rank` | - | 1-indexed |

注：`TrendingSnapshot` ORM 当前没存 `full_name`/`topics`/`homepage`(只存 rank/stars_today/language/description/repo_id)。**本 spec 不改 schema**,`full_name` 暂用 `description` 首行截断作为回退显示。

### 1.5 非目标

- ❌ embedding 相似度(T008 用关键字精确匹配,embedding 阶段二)
- ❌ 用户偏好权重衰减
- ❌ 推送调度(T015 推送,本 TODO 只产出 dict 列表)
- ❌ DB 写(返回 dict 不落库,落库由 T015 RecommendationRepository)

---

## B2. 验收

| AC | 断言 | 怎么验 |
|---|---|---|
| AC-1 | `compute_repo_score` 命中一个 user_keyword → 返回 (score > 0, ["term"]) | 单测 |
| AC-2 | 没命中任何 keyword → score = log(stars_today+2) 无 keyword 加成 | 单测 |
| AC-3 | 多关键字命中,score 累加 | 单测:3 个命中 → 验证算式 |
| AC-4 | stars_today=None → log(0+2)≈0.693 | 单测 |
| AC-5 | 关键字大小写不敏感(描述大写 "Python" 也命中 keyword "python") | 单测 |
| AC-6 | `rank_recommendations` 跳过已 star 的 repo | 单测:stars 含 repo_id=1 → trending 含 repo_id=1 → 不在结果 |
| AC-7 | `rank_recommendations` 跳过 7 天内已推荐(repo_id=2 → 传 already_recommended_ids={2}) | 单测 |
| AC-8 | top_n 限制返回数 | 单测:top_n=3 → len <= 3 |
| AC-9 | min_score 过滤低分 | 单测:min_score=100 → 空列表 |
| AC-10 | 按 score 降序 | 单测:验证降序 |
| AC-11 | 50 star → TF-IDF 产出 ≥ 30 keywords → 喂给 25 trending → ≥ 1 推荐(有命中) | 集成测试 |
| AC-12 | 空 stars(没星过任何 repo)→ 退化为仅用 user_keywords,仍能产推荐 | 单测 |
| AC-13 | 关键字命中分两种(显式 5.0 vs TF-IDF weight*1.0)混合 | 单测:验证两路相加 |

---

## B3. 测试矩阵

| C | 维度 | 覆盖 |
|---|---|---|
| C1 功能 | 单 repo 打分 | AC-1 / AC-2 / AC-3 |
| C2 边界 | stars_today None | AC-4 |
| C3 边界 | 大小写 | AC-5 |
| C4 功能 | 跳过 star 过 | AC-6 |
| C5 功能 | 7-day dedupe | AC-7 |
| C6 边界 | top_n / min_score | AC-8 / AC-9 |
| C7 排序 | 降序 | AC-10 |
| C8 集成 | 50 star → 推荐 | AC-11 |
| C9 边界 | 空 stars 退化 | AC-12 |
| C10 边界 | 关键字权重混合 | AC-13 |

测试文件:`tests/unit/recommender/test_pipeline.py`

---

## B4. 风险

- **R1**：TrendingSnapshot ORM 没 full_name,推荐 dict 没 full_name 显示不全。**缓解**：T015 推送时去 GitHub API 拉详情补全,或阶段二 schema 升级。
- **R2**：TF-IDF 在 0 star 场景退化为空。**缓解**：AC-12 验证退化路径不报错。
- **R3**：精确匹配错过词形变(learn/learning/leaned)。**缓解**：spec 内明示,阶段二加 lemmatization。
- **R4**：`description` 空字符串命中多。**缓解**：repo_text 加 `topics + language` 拼接,描述空时仍能命中 language。
- **R5**：`log(stars_today+2)` 用 `math.log`,stars_today None 时 fallback 1.0。