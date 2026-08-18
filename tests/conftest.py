"""Shared pytest fixtures for ai-github-radar tests.

所有 fixture 写入项目内的 tmp_path / 临时 SQLite,不污染用户目录
(AGENTS.md §6 沙箱硬约束)。
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """每个测试把 cwd 切到 tmp_path,防止 .env / DB 污染用户目录。"""
    monkeypatch.chdir(tmp_path)


@pytest.fixture()
def sample_env_file(tmp_path: Path) -> Path:
    """一个最小可用的 .env 样本,供 config 测试用。"""
    env = tmp_path / ".env"
    env.write_text(
        "GITHUB_TOKEN=ghp_test_token_xxxxxxxxxxxxxxxxxxxx\n"
        "RADAR_USER=test-user\n"
        "RADAR_PUSH_TARGET=local\n"
        "RADAR_FETCH_INTERVAL=daily\n",
        encoding="utf-8",
    )
    return env


@pytest.fixture()
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """清空所有 RADAR_* / GITHUB_* 环境变量,保证 .env 加载行为可预测。"""
    for key in list(os.environ):
        if key.startswith(("RADAR_", "GITHUB_", "OPENAI_", "ANTHROPIC_")):
            monkeypatch.delenv(key, raising=False)