"""T001 项目骨架测试。"""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"


def test_ac1_package_importable() -> None:
    """AC-1: import ai_github_radar 成功。"""
    mod = importlib.import_module("ai_github_radar")
    assert mod is not None


def test_ac2_version_matches_pyproject() -> None:
    """AC-2 + C5: __version__ 等于 pyproject.toml [project].version。"""
    mod = importlib.import_module("ai_github_radar")
    pyproject_text = PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', pyproject_text, re.MULTILINE)
    assert m is not None, "pyproject.toml 缺少 version 字段"
    assert mod.__version__ == m.group(1)


def test_c3_module_has_docstring() -> None:
    """C3: 模块 docstring 非空且含项目关键词。"""
    mod = importlib.import_module("ai_github_radar")
    assert mod.__doc__ is not None
    assert "AI" in mod.__doc__ or "GitHub" in mod.__doc__


def test_c4_hyphenated_name_is_not_importable() -> None:
    """C4: ai-github-radar(连字符) 不是合法 Python 标识符,import 应失败。"""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("ai-github-radar")


def test_c6_no_heavy_imports() -> None:
    """C6: __init__.py 不引入 numpy / sklearn / github / sqlalchemy 等重依赖。"""
    mod = importlib.import_module("ai_github_radar")
    heavy = ("numpy", "sklearn", "github", "sqlalchemy", "typer", "rich")
    leaked = [name for name in heavy if name in sys.modules]
    # 任何重依赖若已被 import,记下来;但允许它们在 sys.modules(因为 pytest 已 import)
    # 我们只检查 ai_github_radar 自身没主动 import 它们
    src_text = (REPO_ROOT / "backend" / "ai_github_radar" / "__init__.py").read_text(
        encoding="utf-8"
    )
    for dep in heavy:
        assert f"import {dep}" not in src_text, (
            f"__init__.py 不应主动 import {dep};"
            f" 重依赖应按需在子模块 import"
        )
    assert mod is not None