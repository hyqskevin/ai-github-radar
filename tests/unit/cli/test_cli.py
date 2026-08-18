"""T012 cli 测试。"""

from __future__ import annotations

from click.testing import CliRunner

from ai_github_radar.cli import cli


# ---------------------------------------------------------------------------
# help / 结构
# ---------------------------------------------------------------------------


def test_ac1_root_help_no_error() -> None:
    """AC-1: python -m ai_github_radar.cli --help 不报错。"""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.output
    assert "scan" in result.output
    assert "keyword" in result.output


def test_ac2_init_help() -> None:
    """AC-2: radar init --help。"""
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "--help"])
    assert result.exit_code == 0
    assert "--user" in result.output
    assert "--no-llm" in result.output


def test_ac3_scan_help() -> None:
    """AC-3: radar scan --help。"""
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--push" in result.output
    assert "--top" in result.output


def test_ac4_keyword_subcommands_listed() -> None:
    """AC-4: radar keyword --help 列 list/add/del/toggle。"""
    runner = CliRunner()
    result = runner.invoke(cli, ["keyword", "--help"])
    assert result.exit_code == 0
    for cmd in ("list", "add", "del", "toggle"):
        assert cmd in result.output


def test_ac15_exit_code_zero_on_normal_path() -> None:
    """AC-15: CLI exit code = 0 on 正常路径。"""
    runner = CliRunner()
    result = runner.invoke(cli, ["keyword", "--help"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# keyword 子命令 (需要 in-memory DB,隔离 settings)
# ---------------------------------------------------------------------------


def _make_keyword_runner(tmpdir: str) -> CliRunner:
    """构造隔离 cwd 的 CliRunner,并预先建好 DB 表。"""
    import os
    from ai_github_radar.db import Base
    from ai_github_radar.storage.db import reset_for_testing, init_db

    cwd_orig = os.getcwd()
    os.chdir(tmpdir)
    # reset 单例(因为 _engine / _factory 是 module-level cached)
    reset_for_testing()
    # 用 cwd-relative path(默认 db_url)
    init_db()
    return CliRunner(), cwd_orig


def test_ac5_keyword_list_echoes_table(tmp_path) -> None:
    """AC-5: radar keyword list echo 关键字表。"""
    import os
    from ai_github_radar.storage.repositories import KeywordRepository
    from ai_github_radar.storage.db import session_scope

    runner, cwd_orig = _make_keyword_runner(str(tmp_path))
    try:
        # 先 seed
        with session_scope() as s:
            KeywordRepository(s).add("agent", weight=5.0)
        result = runner.invoke(cli, ["keyword", "list"])
        assert result.exit_code == 0, result.output
        assert "agent" in result.output
    finally:
        os.chdir(cwd_orig)


def test_ac6_keyword_add_calls_repo_add(tmp_path) -> None:
    """AC-6: radar keyword add X 调 repo.add("X")。"""
    import os
    runner, cwd_orig = _make_keyword_runner(str(tmp_path))
    try:
        result = runner.invoke(cli, ["keyword", "add", "python", "--weight", "5.0"])
        assert result.exit_code == 0, result.output
        assert "added" in result.output.lower()
    finally:
        os.chdir(cwd_orig)


def test_ac7_keyword_del_calls_repo_delete(tmp_path) -> None:
    """AC-7: radar keyword del X 调 repo.delete。"""
    import os
    from ai_github_radar.storage.repositories import KeywordRepository
    from ai_github_radar.storage.db import session_scope

    runner, cwd_orig = _make_keyword_runner(str(tmp_path))
    try:
        with session_scope() as s:
            KeywordRepository(s).add("to_delete")
        result = runner.invoke(cli, ["keyword", "del", "to_delete"])
        assert result.exit_code == 0, result.output
        assert "deleted" in result.output.lower()
    finally:
        os.chdir(cwd_orig)


def test_ac8_keyword_toggle_calls_repo_toggle(tmp_path) -> None:
    """AC-8: radar keyword toggle X 调 repo.toggle。"""
    import os
    from ai_github_radar.storage.repositories import KeywordRepository
    from ai_github_radar.storage.db import session_scope

    runner, cwd_orig = _make_keyword_runner(str(tmp_path))
    try:
        with session_scope() as s:
            KeywordRepository(s).add("agent")
        result = runner.invoke(cli, ["keyword", "toggle", "agent"])
        assert result.exit_code == 0, result.output
        assert "enabled" in result.output.lower()
    finally:
        os.chdir(cwd_orig)