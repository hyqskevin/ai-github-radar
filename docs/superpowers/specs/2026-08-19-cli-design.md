# Spec — T012 cli/

| 维度 | 内容 |
|---|---|
| **TODO ID** | T012（docs/TODO.md §CLI + 周期） |
| **作者** | ai-github-radar 维护者 + AI 助手（2026-08-19） |
| **优先级** | 高 — 产品闭环入口 |
| **触发** | docs/TODO.md T012 |

---

## B1. 设计

### 1.1 目标

实现 `src/ai_github_radar/cli/`,基于 `click` 的命令行入口:

```
radar init    [--user NAME] [--no-llm]     # 拉 stars + 提关键字 + 入库
radar scan    [--push TARGET] [--top N]    # 拉 trending + 匹配 + 推送
radar keyword list                        # 关键字列表
radar keyword add <term>                  # 加关键字
radar keyword del <term|id>               # 删
radar keyword toggle <term|id>            # 启/停
radar web     [--port PORT]               # 起 FastAPI UI(占位,T013 真实实现)
```

`radar` = Python 包 `__main__.py`,扫描 `cli/__init__.py` 的 `cli` group。

### 1.2 模块拆分

```
src/ai_github_radar/cli/
├── __init__.py     # 暴露 cli group
├── __main__.py     # python -m ai_github_radar.cli
├── init_cmd.py     # radar init
├── scan_cmd.py     # radar scan
├── keyword_cmd.py  # radar keyword {list,add,del,toggle}
└── web_cmd.py      # radar web(占位,T013)
```

### 1.3 init 命令细节

```python
@cli.command()
@click.option("--user", default=None, help="GitHub username(默认从 config 读)")
@click.option("--no-llm", is_flag=True, help="强制走 TF-IDF,不用 LLM")
def init(user: str | None, no_llm: bool):
    """拉 stars + 提关键字 + 入库."""
    settings = get_settings()
    user = user or settings.radar_user
    # 1. 拉 stars(GitHub API)
    stars = github_client.fetch_stars(user)
    # 2. 入库
    storage.upsert_stars(stars)
    # 3. 提关键字
    if no_llm or detect_provider() is None:
        kw_results = extract_keywords_tf_idf(...)
    else:
        kw_results = extract_keywords_via_llm(...)
    # 4. 入库
    keyword_repo.bulk_upsert_from_tfidf(kw_results)
    click.echo(f"✓ initialized {len(stars)} stars, {n} keywords")
```

### 1.4 scan 命令细节

```python
@cli.command()
@click.option("--push", default="local", type=click.Choice(["local", "feishu", "email", "stdout"]))
@click.option("--top", default=10)
.get("top")
def scan(push: str, top: int):
    """拉 trending + 匹配 + 推送."""
    # 1. 拉 trending
    trending = trending.fetch_trending_html()
    # 2. 取 stars + keywords from DB
    stars = storage.list_stars()
    kws = storage.list_keywords(enabled_only=True)
    # 3. 算 7-day dedupe 集合
    rec_ids = storage.list_recommended_ids(days=7)
    # 4. 匹配
    recs = rank_recommendations(stars, trending, kws, top_n=top, already_recommended_ids=rec_ids)
    # 5. 推送
    if push == "local": local.write_recommendations(recs)
    elif push == "feishu": feishu.push_feishu(recs, ...)
    elif push == "email": email.push_email(recs, ...)
    elif push == "stdout": print(render_json(recs))
```

### 1.5 非目标

- ❌ 子命令的细节 config(T012 直接读 get_settings())
- ❌ 异步 / 并发(T015 scheduler 处理)
- ❌ 进度条(阶段二)

---

## B2. 验收

| AC | 断言 | 怎么验 |
|---|---|---|
| AC-1 | `python -m ai_github_radar.cli --help` 不报错 | 单测 CliRunner |
| AC-2 | `radar init --help` 列选项 | CliRunner |
| AC-3 | `radar scan --help` 列 --push / --top 选项 | CliRunner |
| AC-4 | `radar keyword --help` 显示子命令 | CliRunner |
| AC-5 | `radar keyword list` 调 repo.list() 并 echo | CliRunner + mock repo |
| AC-6 | `radar keyword add X` 调 repo.add("X") | CliRunner + mock |
| AC-7 | `radar keyword del X` 调 repo.delete("X") | CliRunner + mock |
| AC-8 | `radar keyword toggle X` 调 repo.toggle | CliRunner + mock |
| AC-9 | `radar init` 编排:fetch_stars + TF-IDF + bulk_upsert | CliRunner + patch |
| AC-10 | `radar init --no-llm` 强制 TF-IDF 不调 LLM | patch |
| AC-11 | `radar scan --push local` 调 write_recommendations | CliRunner + patch |
| AC-12 | `radar scan --push feishu` 调 push_feishu | CliRunner + patch |
| AC-13 | `radar scan --push email` 调 push_email | CliRunner + patch |
| AC-14 | `radar scan --push stdout` 打印 JSON | CliRunner + capsys |
| AC-15 | CLI exit code = 0 on 正常路径 | CliRunner.exit_code |

---

## B3. 测试矩阵

| C | 维度 | 覆盖 |
|---|---|---|
| C1 CLI | help / 结构 | AC-1..AC-4 |
| C2 keyword | 子命令 | AC-5..AC-8 |
| C3 init | 编排 | AC-9 / AC-10 |
| C4 scan | 推送路由 | AC-11..AC-14 |
| C5 CLI | exit code | AC-15 |

测试文件：
- `tests/unit/cli/test_init.py`
- `tests/unit/cli/test_scan.py`
- `tests/unit/cli/test_keyword.py`

---

## B4. 风险

- **R1**：`click` 已在 pyproject。
- **R2**：DB session 在 click 命令里管理 —— 用 `session_scope` context manager,T014 包装。
- **R3**：mock `get_settings()` 避免读 .env。
- **R4**：测试用 `click.testing.CliRunner` + `isolated_filesystem` 隔离 cwd。