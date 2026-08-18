"""T009 push/local.py 测试。"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from ai_github_radar.push.local import (
    render_json,
    render_markdown,
    write_recommendations,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_recs() -> list[dict]:
    """2 条推荐 dict(模拟 T008 输出)。"""
    return [
        {
            "repo_id": 100,
            "full_name": "owner1/repo1",
            "description": "Python FastAPI web framework with async support",
            "language": "Python",
            "score": 12.34,
            "matched_keywords": ["fastapi", "async"],
            "rank": 1,
            "stars_today": 200,
        },
        {
            "repo_id": 200,
            "full_name": "owner2/repo2",
            "description": "Rust 嵌入式 async runtime for no_std systems",
            "language": "Rust",
            "score": 9.5,
            "matched_keywords": ["embedded"],
            "rank": 2,
            "stars_today": 80,
        },
    ]


@pytest.fixture()
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> str:
    """freeze time 到 2026-08-19,return ISO date。"""
    fixed = datetime(2026, 8, 19, 12, 0, 0, tzinfo=timezone.utc)
    import ai_github_radar.push.local as local_mod
    monkeypatch.setattr(local_mod, "_utcnow", lambda: fixed)
    return "2026-08-19"


# ---------------------------------------------------------------------------
# render_markdown
# ---------------------------------------------------------------------------


def test_ac1_markdown_contains_date_and_title(sample_recs: list[dict]) -> None:
    """AC-1: Markdown 含日期 + 标题。"""
    out = render_markdown(sample_recs, date="2026-08-19", generated_at="2026-08-19T12:00:00+00:00")
    assert "2026-08-19" in out
    assert "GitHub Radar" in out


def test_ac2_markdown_has_h1_header(sample_recs: list[dict]) -> None:
    """AC-2: H1 标题。"""
    out = render_markdown(sample_recs, date="2026-08-19", generated_at="2026-08-19T12:00:00+00:00")
    assert "# GitHub Radar 推荐 — 2026-08-19" in out


def test_ac3_each_rec_renders_fields(sample_recs: list[dict]) -> None:
    """AC-3: 每条 rec 含 full_name + description + score + matched_keywords。"""
    out = render_markdown(sample_recs, date="2026-08-19", generated_at="2026-08-19T12:00:00+00:00")
    assert "owner1/repo1" in out
    assert "Python FastAPI" in out
    assert "12.340" in out  # score
    assert "owner2/repo2" in out
    assert "Rust" in out


def test_ac4_language_emoji_mapping(sample_recs: list[dict]) -> None:
    """AC-4: language → emoji。"""
    out = render_markdown(sample_recs, date="2026-08-19", generated_at="2026-08-19T12:00:00+00:00")
    assert "🐍" in out  # Python
    assert "🦀" in out  # Rust


def test_ac5_matched_keywords_inline_code(sample_recs: list[dict]) -> None:
    """AC-5: matched keywords 渲染为 `term`。"""
    out = render_markdown(sample_recs, date="2026-08-19", generated_at="2026-08-19T12:00:00+00:00")
    assert "`fastapi`" in out
    assert "`async`" in out
    assert "`embedded`" in out


def test_ac14_markdown_contains_github_link(sample_recs: list[dict]) -> None:
    """AC-14: Markdown 含 GitHub HTML 链接。"""
    out = render_markdown(sample_recs, date="2026-08-19", generated_at="2026-08-19T12:00:00+00:00")
    assert "https://github.com/owner1/repo1" in out
    assert "https://github.com/owner2/repo2" in out


def test_markdown_handles_unknown_language() -> None:
    """未知 language → 默认 📦。"""
    recs = [{"repo_id": 1, "full_name": "o/r", "description": "x",
             "language": "COBOL", "score": 5.0, "matched_keywords": [],
             "rank": 1, "stars_today": 10}]
    out = render_markdown(recs, date="2026-08-19", generated_at="2026-08-19T12:00:00+00:00")
    assert "📦" in out


def test_markdown_handles_null_description() -> None:
    """description=None → 不崩,不显示空段。"""
    recs = [{"repo_id": 1, "full_name": "o/r", "description": None,
             "language": "Python", "score": 5.0, "matched_keywords": [],
             "rank": 1, "stars_today": 10}]
    out = render_markdown(recs, date="2026-08-19", generated_at="2026-08-19T12:00:00+00:00")
    assert "owner1/repo" not in out  # 不应在 out
    assert "o/r" in out


# ---------------------------------------------------------------------------
# render_json
# ---------------------------------------------------------------------------


def test_ac6_json_valid_and_indented(sample_recs: list[dict]) -> None:
    """AC-6: render_json 合法 + indent=2 + ensure_ascii=False。"""
    out = render_json(sample_recs)
    data = json.loads(out)  # parse 成功
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["full_name"] == "owner1/repo1"
    # indent=2 → 多行
    assert "\n  " in out


def test_json_preserves_chinese(sample_recs: list[dict]) -> None:
    """中文 description 不被转义(ensure_ascii=False)。"""
    recs = [{"repo_id": 1, "full_name": "o/r",
             "description": "中文描述测试 αβγ",
             "language": "Python", "score": 5.0, "matched_keywords": ["测试"],
             "rank": 1, "stars_today": 10}]
    out = render_json(recs)
    assert "中文描述测试" in out
    assert "测试" in out
    # 验证不被 \uXXXX 转义
    assert "\\u" not in out


# ---------------------------------------------------------------------------
# write_recommendations
# ---------------------------------------------------------------------------


def test_ac7_default_path_creates_md(tmp_path: Path, sample_recs: list[dict],
                                      fixed_today: str) -> None:
    """AC-7: 默认路径 ./data/recommendations/YYYY-MM-DD.md。"""
    # 切 cwd 到 tmp
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        p = write_recommendations(sample_recs)
    finally:
        os.chdir(cwd)
    assert p is not None
    # 用 resolve() 避免 macOS /private/var 前缀
    assert p.resolve() == (tmp_path / "data" / "recommendations" / "2026-08-19.md").resolve()
    assert p.exists()
    content = p.read_text()
    assert "# GitHub Radar" in content


def test_ac7_default_path_creates_json(tmp_path: Path, sample_recs: list[dict],
                                        fixed_today: str) -> None:
    """JSON 格式默认路径 YYYY-MM-DD.json。"""
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        p = write_recommendations(sample_recs, format="json")
    finally:
        os.chdir(cwd)
    assert p.resolve() == (tmp_path / "data" / "recommendations" / "2026-08-19.json").resolve()
    data = json.loads(p.read_text())
    assert len(data) == 2


def test_ac8_custom_output_dir(tmp_path: Path, sample_recs: list[dict],
                                fixed_today: str) -> None:
    """AC-8: 自定义 output_dir 生效。"""
    p = write_recommendations(sample_recs, output_dir=tmp_path / "my_reports")
    assert p == tmp_path / "my_reports" / "2026-08-19.md"


def test_ac9_custom_output_file(tmp_path: Path, sample_recs: list[dict]) -> None:
    """AC-9: output_file 覆盖路径。"""
    custom = tmp_path / "report-2026.md"
    p = write_recommendations(sample_recs, output_file=custom)
    assert p == custom
    assert custom.exists()


def test_ac10_stdout_does_not_write_file(
    tmp_path: Path, sample_recs: list[dict], capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-10: stdout=True → 打到 stdout,无文件。"""
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = write_recommendations(sample_recs, stdout=True)
    finally:
        os.chdir(cwd)
    assert result is None
    # data/recommendations 不应被创建
    assert not (tmp_path / "data" / "recommendations").exists()
    # stdout 有输出
    captured = capsys.readouterr()
    assert "# GitHub Radar" in captured.out


def test_ac10_stdout_json(
    tmp_path: Path, sample_recs: list[dict], capsys: pytest.CaptureFixture[str]
) -> None:
    """stdout + format=json 也工作。"""
    result = write_recommendations(sample_recs, stdout=True, format="json")
    assert result is None
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert len(data) == 2


def test_ac11_parent_dir_created_automatically(tmp_path: Path, sample_recs: list[dict],
                                                fixed_today: str) -> None:
    """AC-11: 嵌套父目录自动创建。"""
    deep = tmp_path / "a" / "b" / "c"
    p = write_recommendations(sample_recs, output_dir=deep)
    assert p.exists()
    assert p.parent == deep


def test_ac12_empty_recs_produces_valid_markdown(tmp_path: Path, fixed_today: str) -> None:
    """AC-12: 空 recs → 合法 Markdown(0 条)。"""
    p = write_recommendations([], output_dir=tmp_path)
    content = p.read_text()
    assert "# GitHub Radar" in content
    assert "0" in content  # 0 条


def test_ac13_date_none_uses_today(tmp_path: Path, sample_recs: list[dict],
                                    fixed_today: str) -> None:
    """AC-13: date=None → 用今天 UTC。"""
    p = write_recommendations(sample_recs, output_dir=tmp_path)
    assert "2026-08-19" in p.name


def test_format_invalid_raises(tmp_path: Path, sample_recs: list[dict]) -> None:
    """未知 format → ValueError。"""
    with pytest.raises(ValueError):
        write_recommendations(sample_recs, output_dir=tmp_path, format="xml")  # type: ignore[arg-type]


def test_stdout_and_output_file_conflict_raises(sample_recs: list[dict]) -> None:
    """stdout + output_file 同时给 → ValueError。"""
    with pytest.raises(ValueError):
        write_recommendations(sample_recs, stdout=True, output_file="/tmp/x.md")


def test_write_utf8_chinese(tmp_path: Path, fixed_today: str) -> None:
    """中文 description 写入文件不被 mojibake。"""
    recs = [{"repo_id": 1, "full_name": "o/r",
             "description": "中文描述 αβγ",
             "language": "Python", "score": 5.0, "matched_keywords": ["中文"],
             "rank": 1, "stars_today": 10}]
    p = write_recommendations(recs, output_dir=tmp_path)
    raw = p.read_bytes()
    assert "中文".encode("utf-8") in raw