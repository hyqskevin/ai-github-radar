# Spec — T009 push/local.py

| 维度 | 内容 |
|---|---|
| **TODO ID** | T009（docs/TODO.md §推送） |
| **作者** | ai-github-radar 维护者 + AI 助手（2026-08-19） |
| **优先级** | 高 — `scan` 命令默认输出 |
| **触发** | docs/TODO.md T009 + 用户决策（路径+模板+管道） |

---

## B1. 设计

### 1.1 目标

实现 `src/ai_github_radar/push/local.py`，**本地文件推送**：

- **Markdown 输出** —— 给人读，table + emoji + 仓库链接
- **JSON 输出** —— 给程序消费，完整字段
- **stdout 管道** —— `cat | less` 或 `... | jq` 也能用

### 1.2 路径策略

默认输出根：`./data/recommendations/`（相对 cwd）

| 格式 | 文件 | 命名 |
|---|---|---|
| Markdown | `data/recommendations/YYYY-MM-DD.md` | 一日一文件 |
| JSON | `data/recommendations/YYYY-MM-DD.json` | 一日一文件 |

支持覆盖：
- `--output-dir /custom/path` —— 改根
- `--output-file /tmp/foo.md` —— 改具体文件（同时 `--format md`）
- `--format json` —— 切格式
- `--stdout` —— 打到 stdout 不写文件

### 1.3 jinja2 模板

Markdown 模板 inline 在 Python（不外挂文件，简化分发）：

```markdown
# GitHub Radar 推荐 — {{ date }}

> 生成时间: {{ generated_at }}  |  候选: {{ recs|length }} 条

{% for rec in recs %}
## {{ loop.index }}. {{ rec.language_emoji }} [{{ rec.full_name }}]({{ rec.html_url }})

{% if rec.description %}{{ rec.description }}{% endif %}

- **Score**: `{{ "%.3f"|format(rec.score) }}`
- **Stars today**: {{ rec.stars_today or "—" }}
- **Matched keywords**: {{ rec.matched_keywords|map('`{}`'.format)|join(', ') }}

---
{% endfor %}
```

`language_emoji` 是 helper，常见语言映射 emoji：
- Python → 🐍, Rust → 🦀, TypeScript → 📘, Go → 🐹, Java → ☕, ...

### 1.4 API

```python
def render_markdown(
    recs: list[dict],
    *,
    date: str,                    # "2026-08-19"
    generated_at: str,            # ISO
) -> str:
    """jinja2 渲染 Markdown。"""

def render_json(
    recs: list[dict],
    *,
    indent: int = 2,
) -> str:
    """JSON 序列化(utf-8 / ensure_ascii=False / indent=2)。"""

def write_recommendations(
    recs: list[dict],
    *,
    output_dir: str | Path = "./data/recommendations",
    date: str | None = None,      # None → today UTC
    format: Literal["md", "json"] = "md",
    output_file: str | Path | None = None,  # 覆盖 output_dir+date 路径
    stdout: bool = False,
) -> Path | None:
    """主入口。

    返回:写入的文件 Path(stdout 时返回 None)。
    行为:
      - stdout=True → 打到 stdout,不写文件
      - output_file 提供 → 写到该文件(自动创建父目录)
      - 否则 → output_dir/YYYY-MM-DD.{md|json}
    """
```

### 1.5 非目标

- ❌ Feishu / Email 推送(T010 / T011)
- ❌ HTML 渲染(T013 web 端)
- ❌ 文件清理/归档(阶段二 T209)

---

## B2. 验收

| AC | 断言 | 怎么验 |
|---|---|---|
| AC-1 | `render_markdown` 含日期 + 推荐标题 | 单测 |
| AC-2 | Markdown 含 `# GitHub Radar 推荐 — DATE` H1 | 单测 |
| AC-3 | 每条 rec 渲染 full_name + description + score + matched_keywords | 单测 |
| AC-4 | `language_emoji` 给 Python→🐍 Rust→🦀 TypeScript→📘 其他→📦 | 单测 |
| AC-5 | matched_keywords 渲染为 inline code | 单测:含 ` `python` ` |
| AC-6 | `render_json` 合法 JSON,indent=2,ensure_ascii=False | 单测:json.loads 能 parse + 中文保留 |
| AC-7 | `write_recommendations` 默认路径 `./data/recommendations/YYYY-MM-DD.md` | 单测:tmp_path 验证 |
| AC-8 | 自定义 `output_dir` 生效 | 单测 |
| AC-9 | 自定义 `output_file` 生效 | 单测 |
| AC-10 | `--stdout=True` → 内容打到 stdout,无文件产生 | capsys 单测 |
| AC-11 | 父目录不存在自动创建 | 单测:嵌套 tmp_path |
| AC-12 | 空 recs → 合法 Markdown(只标题 + "0 条"),不报错 | 单测 |
| AC-13 | `date=None` → 用今天 UTC (YYYY-MM-DD) | 单测:freeze time |
| AC-14 | Markdown 含 GitHub HTML 链接 | 单测 |

---

## B3. 测试矩阵

| C | 维度 | 覆盖 |
|---|---|---|
| C1 功能 | Markdown 渲染 | AC-1..AC-3 |
| C2 边界 | language emoji | AC-4 |
| C3 边界 | matched keywords inline code | AC-5 |
| C4 功能 | JSON 合法 | AC-6 |
| C5 路径 | 默认路径 | AC-7 |
| C6 路径 | 自定义 dir/file | AC-8 / AC-9 |
| C7 管道 | stdout | AC-10 |
| C8 错误 | 父目录自动建 | AC-11 |
| C9 边界 | 空 recs | AC-12 |
| C10 时间 | today UTC | AC-13 |
| C11 一致性 | Markdown 含 GitHub 链接 | AC-14 |

测试文件：`tests/unit/push/test_local.py`

---

## B4. 风险

- **R1**：jinja2 在 pyproject 已声明依赖。✅
- **R2**：stdout 输出和 CI 友好——capsys 测试隔离。
- **R3**：`date=None` 用 `datetime.now(timezone.utc)`，freeze_time 用 monkeypatch。
- **R4**：路径安全——`output_dir` 含用户路径时不做 sanitize（用户自负责），避免越界做软限制（拒绝 `..` 父级穿越?本期不做，留 TODO T209）。
- **R5**：Markdown 模板 inline 字符串——jinja2 `Template(source)` 直接传字符串，无需文件加载。