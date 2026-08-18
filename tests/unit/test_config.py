"""T002 config.py 测试。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
CONFIG_MODULE = "ai_github_radar.config"


def _run_config(*args: str, env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", CONFIG_MODULE, *args]
    env = {**env, "PYTHONPATH": str(SRC)}
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, env=env, timeout=15
    )


@pytest.fixture()
def valid_env_file(tmp_path: Path) -> Path:
    """最小合法 .env:GitHub token + radar_user。"""
    env = tmp_path / ".env"
    env.write_text(
        "GITHUB_TOKEN=ghp_test_token_xxx\n"
        "RADAR_USER=test-user\n",
        encoding="utf-8",
    )
    return env


def test_ac1_valid_env_validate_exit_zero(valid_env_file: Path, clean_env) -> None:
    """AC-1: 合法 .env 下 --validate 退出码 0 + stdout 含 OK。"""
    env = dict(os.environ)
    env["RADAR_CONFIG_PATH"] = str(valid_env_file)
    result = _run_config("--validate", env=env, cwd=valid_env_file.parent)
    assert result.returncode == 0, f"stderr={result.stderr!r} stdout={result.stdout!r}"
    assert "OK" in result.stdout


def test_ac2_missing_required_token_exits_2(tmp_path: Path, clean_env) -> None:
    """AC-2: 缺 GITHUB_TOKEN 时报具体字段名,exit 2。"""
    env_file = tmp_path / ".env"
    env_file.write_text("RADAR_USER=test-user\n", encoding="utf-8")
    env = dict(os.environ)
    env["RADAR_CONFIG_PATH"] = str(env_file)
    result = _run_config("--validate", env=env, cwd=tmp_path)
    assert result.returncode == 2
    assert "github_token" in result.stdout or "github_token" in result.stderr


def test_ac3_feishu_target_without_webhook_exits_2(tmp_path: Path, clean_env) -> None:
    """AC-3: push=feishu 但无 webhook 报错。"""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GITHUB_TOKEN=ghp_test\n"
        "RADAR_USER=test-user\n"
        "RADAR_PUSH_TARGET=feishu\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["RADAR_CONFIG_PATH"] = str(env_file)
    result = _run_config("--validate", env=env, cwd=tmp_path)
    assert result.returncode == 2
    combined = result.stdout + result.stderr
    assert "feishu_webhook_url" in combined


def test_ac4_load_settings_singleton(tmp_path: Path, clean_env) -> None:
    """AC-4: load_settings() 返回单例。"""
    # 建一个最小 .env,monkeypatch 设过 env 后 clean_env 会清空,所以走文件路径
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GITHUB_TOKEN=ghp_test\nRADAR_USER=u\n", encoding="utf-8"
    )
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setenv("RADAR_CONFIG_PATH", str(env_file))
        monkeypatch.chdir(tmp_path)
        from ai_github_radar.config import load_settings

        s1 = load_settings()
        s2 = load_settings()
        assert s1 is s2
    finally:
        monkeypatch.undo()


def test_ac5_secret_str_does_not_leak(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-5: SecretStr 字段 repr 不含明文。"""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_leak_me_DO_NOT_PRINT")
    monkeypatch.setenv("RADAR_USER", "u")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-leak_me_DO_NOT_PRINT")
    from ai_github_radar.config import load_settings

    load_settings.cache_clear()
    s = load_settings()
    rep = repr(s)
    assert "sk-leak_me_DO_NOT_PRINT" not in rep
    # openai_api_key 默认 None(无 env 文件),直接 setenv 时 Pydantic 会读到
    if s.openai_api_key is not None:
        assert "sk-leak_me_DO_NOT_PRINT" not in repr(s.openai_api_key)


def test_ac6_error_message_does_not_print_token(tmp_path: Path, clean_env) -> None:
    """AC-6: 故意让 smtp_password 校验失败,stdout/stderr 不含密码明文。"""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GITHUB_TOKEN=ghp_test\n"
        "RADAR_USER=test-user\n"
        "RADAR_PUSH_TARGET=email\n"
        "SMTP_HOST=smtp.example.com\n"
        "SMTP_PORT=587\n"
        "SMTP_USER=test@example.com\n"
        "SMTP_PASSWORD=SECRET_PASSWORD_VALUE_XYZ\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["RADAR_CONFIG_PATH"] = str(env_file)
    result = _run_config("--validate", env=env, cwd=tmp_path)
    assert result.returncode == 2  # 缺 smtp_to
    combined = result.stdout + result.stderr
    assert "SECRET_PASSWORD_VALUE_XYZ" not in combined


def test_c7_username_with_special_chars(tmp_path: Path, clean_env) -> None:
    """C7: GitHub username 含连字符 / 下划线 / 数字。"""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GITHUB_TOKEN=ghp_test\nRADAR_USER=user-name_123\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["RADAR_CONFIG_PATH"] = str(env_file)
    result = _run_config("--validate", env=env, cwd=tmp_path)
    assert result.returncode == 0


def test_c8_field_name_case_insensitive(tmp_path: Path, clean_env) -> None:
    """C8: .env 大小写不敏感(github_token / GITHUB_TOKEN 都识别)。"""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "github_token=ghp_test\nradar_user=u\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["RADAR_CONFIG_PATH"] = str(env_file)
    result = _run_config("--validate", env=env, cwd=tmp_path)
    assert result.returncode == 0


def test_c9_default_values_match_spec(clean_env) -> None:
    """C9: 默认值与 SPEC.md §3 一致。"""
    # 不写 RADAR_FETCH_INTERVAL → 应是 "daily"
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        monkeypatch.setenv("RADAR_USER", "u")
        from ai_github_radar.config import load_settings

        load_settings.cache_clear()
        s = load_settings()
        assert s.radar_fetch_interval == "daily"
        assert s.radar_push_target == "local"
        assert str(s.db_url) == "sqlite:///./data/radar.db"
    finally:
        monkeypatch.undo()


def test_c10_missing_env_file_exits_2(tmp_path: Path, clean_env) -> None:
    """C10: .env 不存在 → exit 2 + 含路径提示。"""
    env = dict(os.environ)
    env["RADAR_CONFIG_PATH"] = str(tmp_path / "nonexistent.env")
    result = _run_config("--validate", env=env, cwd=tmp_path)
    assert result.returncode == 2
    combined = result.stdout + result.stderr
    assert "nonexistent.env" in combined or "missing" in combined.lower()