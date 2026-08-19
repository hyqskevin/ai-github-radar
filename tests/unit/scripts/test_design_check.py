"""tests/unit/scripts/test_design_check.py — design-check.py 行为."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "design-check.py"


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=cwd or REPO_ROOT,
    )


def test_design_check_ok_in_clean_repo() -> None:
    """真实仓库应 OK(7 token 同步)。"""
    p = _run()
    assert p.returncode == 0, f"stderr={p.stderr}\nstdout={p.stdout}"
    assert "OK — DESIGN.md ↔ main.css 7 token 同步" in p.stdout


def test_design_check_json_output_is_pure_json() -> None:
    """--json 只输出 JSON(没有 OK 行干扰)。"""
    p = _run("--json")
    assert p.returncode == 0
    data = json.loads(p.stdout)  # 纯 JSON 才能 parse
    assert "design_colors" in data
    assert "css_token_names" in data
    for key in ("primary", "secondary", "tertiary", "neutral", "success", "warning", "error"):
        assert key in data["design_colors"]


def test_design_check_detects_missing_token_in_css(tmp_path) -> None:
    """main.css 删掉 primary token → exit 1。"""
    (tmp_path / "DESIGN.md").write_text((REPO_ROOT / "DESIGN.md").read_text())
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "web").mkdir()
    (tmp_path / "app" / "web" / "app").mkdir()
    (tmp_path / "app" / "web" / "app" / "assets").mkdir()
    (tmp_path / "app" / "web" / "app" / "assets" / "css").mkdir()
    # main.css 缺 primary
    (tmp_path / "app" / "web" / "app" / "assets" / "css" / "main.css").write_text(
        "@theme static {\n"
        "  --color-secondary-500: #938F99;\n"
        "  --color-tertiary-500: #4FD8EB;\n"
        "  --color-neutral-500: #1D1B20;\n"
        "  --color-success-500: #7DCE82;\n"
        "  --color-warning-500: #FFB77A;\n"
        "  --color-error-500: #FFB4AB;\n"
        "}\n"
    )
    p = _run("--root", str(tmp_path))
    assert p.returncode == 1
    assert "primary" in p.stderr


def test_design_check_missing_file(tmp_path) -> None:
    """空目录(无 DESIGN.md) → exit 1 + 友好错误。"""
    p = _run("--root", str(tmp_path))
    assert p.returncode == 1
    assert "DESIGN.md" in p.stderr