"""本地文件推送 — T009.

Markdown(jinja2) + JSON + stdout 管道输出。
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from jinja2 import Template


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_DIR = Path("./data/recommendations")


# ---------------------------------------------------------------------------
# 时间
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _today_iso() -> str:
    """今天 UTC,YYYY-MM-DD。"""
    return _utcnow().strftime("%Y-%m-%d")


def _now_iso() -> str:
    """当前 UTC,ISO 8601。"""
    return _utcnow().isoformat()


# ---------------------------------------------------------------------------
# Language → emoji
# ---------------------------------------------------------------------------

_LANGUAGE_EMOJI = {
    "python": "🐍",
    "rust": "🦀",
    "typescript": "📘",
    "javascript": "📒",
    "go": "🐹",
    "java": "☕",
    "kotlin": "🟪",
    "swift": "🟧",
    "ruby": "💎",
    "php": "🐘",
    "c++": "🔷",
    "c#": "🎼",
    "scala": "🔴",
    "haskell": "🎓",
    "elixir": "💜",
    "clojure": "🍀",
    "shell": "🐚",
    "html": "🌐",
    "css": "🎨",
    "vue": "🟢",
}


def _language_emoji(lang: Optional[str]) -> str:
    """常见语言 → emoji,未知 → 📦。"""
    if not lang:
        return "📦"
    return _LANGUAGE_EMOJI.get(lang.lower(), "📦")


# ---------------------------------------------------------------------------
# Markdown 模板
# ---------------------------------------------------------------------------

_MD_TEMPLATE = Template("""# GitHub Radar 推荐 — {{ date }}

> 生成时间: {{ generated_at }}  |  候选: {{ recs|length }} 条
{% if recs|length == 0 %}
_暂无推荐。_
{% endif %}

{% for rec in recs %}
## {{ loop.index }}. {{ rec.language_emoji }} [{{ rec.full_name }}]({{ rec.html_url }})

{% if rec.description %}{{ rec.description }}{% endif %}

- **Score**: `{{ "%.3f"|format(rec.score) }}`
- **Stars today**: {{ rec.stars_today if rec.stars_today is not none else "—" }}
- **Matched keywords**: {% if rec.matched_keywords %}{% for kw in rec.matched_keywords %}`{{ kw }}`{% if not loop.last %}, {% endif %}{% endfor %}{% else %}_none_{% endif %}

---
{% endfor %}
""")


def render_markdown(
    recs: list[dict],
    *,
    date: str,
    generated_at: str,
) -> str:
    """jinja2 渲染 Markdown。

    每个 rec dict 需含:
      repo_id, full_name, description, language, score, matched_keywords,
      stars_today, rank
    """
    enriched: list[dict] = []
    for r in recs:
        full_name = r.get("full_name") or f"unknown/repo_{r.get('repo_id', 0)}"
        enriched.append({
            "repo_id": r.get("repo_id"),
            "full_name": full_name,
            "html_url": f"https://github.com/{full_name}",
            "description": r.get("description"),
            "language": r.get("language"),
            "language_emoji": _language_emoji(r.get("language")),
            "score": r.get("score", 0.0),
            "matched_keywords": r.get("matched_keywords") or [],
            "stars_today": r.get("stars_today"),
            "rank": r.get("rank"),
        })
    return _MD_TEMPLATE.render(
        recs=enriched,
        date=date,
        generated_at=generated_at,
    )


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


def render_json(
    recs: list[dict],
    *,
    indent: int = 2,
) -> str:
    """JSON 序列化(ensure_ascii=False 保留中文)。"""
    return json.dumps(recs, indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# write_recommendations
# ---------------------------------------------------------------------------


Format = Literal["md", "json"]


def write_recommendations(
    recs: list[dict],
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    date: Optional[str] = None,
    format: Format = "md",
    output_file: Optional[str | Path] = None,
    stdout: bool = False,
) -> Optional[Path]:
    """主入口。

    stdout=True:打到 sys.stdout,返回 None(与 output_file 互斥)。
    output_file:覆盖路径(自动 mkdir -p 父目录)。
    否则:output_dir/{date|YYYY-MM-DD}.{md|json}
    """
    if stdout and output_file is not None:
        raise ValueError("stdout=True and output_file=... are mutually exclusive")

    if format not in ("md", "json"):
        raise ValueError(f"format must be 'md' or 'json', got {format!r}")

    # render
    if format == "md":
        d = date or _today_iso()
        content = render_markdown(recs, date=d, generated_at=_now_iso())
    else:  # json
        content = render_json(recs)

    # stdout
    if stdout:
        sys.stdout.write(content)
        if not content.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()
        return None

    # file
    if output_file is not None:
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        return out_path

    # default
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    d = date or _today_iso()
    ext = "md" if format == "md" else "json"
    out_path = out_dir / f"{d}.{ext}"
    out_path.write_text(content, encoding="utf-8")
    return out_path